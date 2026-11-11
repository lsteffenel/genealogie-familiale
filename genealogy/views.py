from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.generic import DetailView, ListView

from .forms import (
    EventProposalForm,
    MediaProposalForm,
    PersonProposalForm,
    ProposalNoteForm,
    ReviewForm,
    UnionProposalForm,
)
from .google_photos import get_media_item_base_url
from .models import EditProposal, Person, ProposalStatus, SiteConfiguration, Union

MAX_TREE_DEPTH = 8


def is_moderator(user):
    return user.is_authenticated and hasattr(user, "profile") and user.profile.is_moderator


class PersonListView(LoginRequiredMixin, ListView):
    model = Person
    template_name = "genealogy/person_list.html"
    context_object_name = "persons"
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get("q", "").strip()
        family = self.request.GET.get("family", "").strip()
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(maiden_name__icontains=query)
            )
        elif family:
            queryset = queryset.filter(last_name__iexact=family)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        family = self.request.GET.get("family", "").strip()
        context["home_html"] = SiteConfiguration.get().home_page_html
        context["query"] = query
        context["family"] = family
        if not query and not family:
            context["mode"] = "families"
            context["families"] = (
                Person.objects.values("last_name")
                .annotate(count=Count("id"))
                .order_by("last_name")
            )
        elif family:
            context["mode"] = "family"
        else:
            context["mode"] = "search"
        return context


class PersonDetailView(LoginRequiredMixin, DetailView):
    model = Person
    template_name = "genealogy/person_detail.html"
    context_object_name = "person"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = self.object
        context["unions"] = [
            (union, union.partner_b if union.partner_a_id == person.pk else union.partner_a)
            for union in list(person.unions_as_a.all()) + list(person.unions_as_b.all())
        ]
        context["parent_unions"] = person.parent_unions.all()
        context["events"] = person.events.all()
        context["media"] = person.media.all()
        context["proposals"] = EditProposal.objects.filter(
            content_type=ContentType.objects.get_for_model(Person),
            object_id=person.pk,
            status=ProposalStatus.PENDING,
        ).select_related("proposed_by", "reviewed_by")
        context["can_propose"] = True
        context["person_photo_url"] = get_media_item_base_url(
            person.google_photo_media_item_id
        )
        context["media_photos"] = [
            (item, get_media_item_base_url(item.google_photo_media_item_id))
            for item in context["media"]
            if item.google_photo_media_item_id
        ]
        return context


def legal_page(request, template):
    return render(request, template)


@login_required
def propose_person_edit(request, pk):
    person = get_object_or_404(Person, pk=pk)
    if request.method == "POST":
        form = PersonProposalForm(request.POST)
        note_form = ProposalNoteForm(request.POST)
        event_form = EventProposalForm(request.POST)
        union_form = UnionProposalForm(request.POST)
        adv_kind = request.POST.get("adv_kind", "")
        advanced_error = None
        advanced = None
        if adv_kind == "event" and event_form.is_filled():
            if event_form.is_valid() and event_form.cleaned_data.get("title"):
                advanced = ("event", event_form.cleaned_data)
            else:
                advanced_error = _(
                    "Section avancée invalide : un titre est requis pour un événement."
                )
        elif adv_kind == "union" and union_form.is_filled():
            if union_form.is_valid() and union_form.cleaned_data.get("partner"):
                advanced = ("union", union_form.cleaned_data)
            else:
                advanced_error = _(
                    "Section avancée invalide : un partenaire est requis pour une union."
                )
        if advanced_error:
            messages.error(request, advanced_error)
        elif form.is_valid() and note_form.is_valid():
            changes = form.changed_fields(person)
            if not changes and not advanced:
                messages.info(request, _("Aucune modification détectée."))
                return redirect("person_detail", pk=person.pk)
            if changes:
                EditProposal.objects.create(
                    content_type=ContentType.objects.get_for_model(Person),
                    object_id=person.pk,
                    field_changes=changes,
                    note=note_form.cleaned_data["note"],
                    proposed_by=request.user,
                )
            if advanced:
                kind, data = advanced
                if kind == "event":
                    new_object_data = {
                        "model": "event",
                        "person_id": person.pk,
                        "event_type": data.get("event_type") or "other",
                        "title": data.get("title", ""),
                        "date": data["date"].isoformat() if data.get("date") else "",
                        "place": data.get("place", ""),
                        "description": data.get("description", ""),
                    }
                else:
                    new_object_data = {
                        "model": "union",
                        "person_id": person.pk,
                        "partner_id": data["partner"].pk,
                        "union_type": data.get("union_type") or "other",
                        "date": data["date"].isoformat() if data.get("date") else "",
                        "place": data.get("place", ""),
                        "notes": data.get("notes", ""),
                    }
                EditProposal.objects.create(
                    action=EditProposal.Action.CREATE,
                    new_object_data=new_object_data,
                    note=note_form.cleaned_data["note"],
                    proposed_by=request.user,
                )
            messages.success(
                request,
                _("Votre proposition a été soumise et est en attente de validation "
                  "par un modérateur."),
            )
            return redirect("person_detail", pk=person.pk)
    else:
        form = PersonProposalForm(instance=person)
        note_form = ProposalNoteForm()
        event_form = EventProposalForm()
        union_form = UnionProposalForm()
    return render(
        request,
        "genealogy/proposal_form.html",
        {
            "form": form,
            "note_form": note_form,
            "person": person,
            "event_form": event_form,
            "union_form": union_form,
        },
    )


@login_required
def tree_view(request, pk=None):
    persons = list(Person.objects.all())
    if not persons:
        return render(request, "genealogy/tree.html", {"root": None, "persons": []})
    by_pk = {p.pk: p for p in persons}

    root_id = pk or request.GET.get("root")
    if root_id:
        root = by_pk.get(int(root_id))
        if root is None:
            raise Http404(_("Personne inconnue"))
    else:
        default_root = SiteConfiguration.get().default_tree_root
        root = default_root if default_root in persons else persons[0]

    show_name = request.GET.get("name", "1") == "1"
    show_dates = request.GET.get("dates", "1") == "1"
    show_photo = request.GET.get("photo", "1") == "1"

    unions = list(Union.objects.prefetch_related("children", "partner_a", "partner_b"))
    family_map = {}
    for union in unions:
        for partner, spouse in (
            (union.partner_a, union.partner_b),
            (union.partner_b, union.partner_a),
        ):
            family_map.setdefault(partner.pk, []).append(
                {
                    "spouse": by_pk[spouse.pk],
                    "union": union,
                    "children": [by_pk[c.pk] for c in union.children.all()],
                }
            )

    for person in persons:
        person.family_entries = family_map.get(person.pk, [])
        person.photo_url = (
            get_media_item_base_url(person.google_photo_media_item_id)
            if show_photo and person.google_photo_media_item_id
            else None
        )

    return render(
        request,
        "genealogy/tree.html",
        {
            "root": root,
            "persons": persons,
            "show_name": show_name,
            "show_dates": show_dates,
            "show_photo": show_photo,
            "max_depth": MAX_TREE_DEPTH,
        },
    )


@login_required
def propose_media_add(request):
    if request.method == "POST":
        form = MediaProposalForm(request.POST, request.FILES)
        if form.is_valid():
            cleaned = form.cleaned_data
            EditProposal.objects.create(
                action=EditProposal.Action.CREATE,
                new_object_data={
                    "model": "media",
                    "person_id": cleaned["person"].pk,
                    "title": cleaned["title"],
                    "description": cleaned["description"],
                    "google_photo_media_item_id": cleaned["google_photo_media_item_id"],
                },
                uploaded_file=cleaned["image"] or None,
                note=cleaned["note"],
                proposed_by=request.user,
            )
            messages.success(
                request,
                _("Votre photo a été soumise et est en attente de validation par un modérateur."),
            )
            return redirect("person_detail", pk=cleaned["person"].pk)
    else:
        form = MediaProposalForm()
    return render(request, "genealogy/media_proposal_form.html", {"form": form})


@user_passes_test(is_moderator)
def proposal_list(request):
    status = request.GET.get("status", ProposalStatus.PENDING)
    proposals = (
        EditProposal.objects.filter(status=status)
        .select_related("proposed_by", "reviewed_by", "content_type")
        .order_by("-created_at")
    )
    return render(
        request,
        "genealogy/proposal_list.html",
        {"proposals": proposals, "status": status,
         "statuses": ProposalStatus.choices},
    )


@user_passes_test(is_moderator)
def proposal_review(request, pk):
    proposal = get_object_or_404(EditProposal, pk=pk, status=ProposalStatus.PENDING)
    if request.method == "POST":
        form = ReviewForm(request.POST)
        action = request.POST.get("action")
        if form.is_valid():
            if action == "approve":
                try:
                    proposal.apply(request.user)
                    messages.success(request, _("Proposition #%(pk)s approuvée et appliquée.") % {"pk": proposal.pk})
                except Exception as exc:
                    messages.error(request, _("Échec de l'application : %(exc)s") % {"exc": exc})
            elif action == "reject":
                proposal.reject(request.user, form.cleaned_data["comment"])
                messages.success(request, _("Proposition #%(pk)s rejetée.") % {"pk": proposal.pk})
            return redirect("proposal_list")
    else:
        form = ReviewForm()
    return render(
        request,
        "genealogy/proposal_review.html",
        {"proposal": proposal, "form": form},
    )
