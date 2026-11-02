from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView

from .forms import PersonProposalForm, ProposalNoteForm, ReviewForm
from .models import EditProposal, Person, ProposalStatus


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
        if query:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(maiden_name__icontains=query)
            )
        return queryset


class PersonDetailView(LoginRequiredMixin, DetailView):
    model = Person
    template_name = "genealogy/person_detail.html"
    context_object_name = "person"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = self.object
        context["unions"] = list(person.unions_as_a.all()) + list(person.unions_as_b.all())
        context["parent_unions"] = person.parent_unions.all()
        context["events"] = person.events.all()
        context["media"] = person.media.all()
        context["proposals"] = EditProposal.objects.filter(
            content_type=ContentType.objects.get_for_model(Person),
            object_id=person.pk,
        ).select_related("proposed_by", "reviewed_by")
        context["can_propose"] = True
        return context


@login_required
def propose_person_edit(request, pk):
    person = get_object_or_404(Person, pk=pk)
    if request.method == "POST":
        form = PersonProposalForm(request.POST)
        note_form = ProposalNoteForm(request.POST)
        if form.is_valid() and note_form.is_valid():
            changes = form.changed_fields(person)
            if not changes:
                messages.info(request, "Aucune modification détectée.")
                return redirect("person_detail", pk=person.pk)
            EditProposal.objects.create(
                content_type=ContentType.objects.get_for_model(Person),
                object_id=person.pk,
                field_changes=changes,
                note=note_form.cleaned_data["note"],
                proposed_by=request.user,
            )
            messages.success(
                request,
                "Votre proposition a été soumise et est en attente de validation "
                "par un modérateur.",
            )
            return redirect("person_detail", pk=person.pk)
    else:
        form = PersonProposalForm(instance=person)
        note_form = ProposalNoteForm()
    return render(
        request,
        "genealogy/proposal_form.html",
        {"form": form, "note_form": note_form, "person": person},
    )


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
                    messages.success(request, f"Proposition #{proposal.pk} approuvée et appliquée.")
                except Exception as exc:
                    messages.error(request, f"Échec de l'application : {exc}")
            elif action == "reject":
                proposal.reject(request.user, form.cleaned_data["comment"])
                messages.success(request, f"Proposition #{proposal.pk} rejetée.")
            return redirect("proposal_list")
    else:
        form = ReviewForm()
    return render(
        request,
        "genealogy/proposal_review.html",
        {"proposal": proposal, "form": form},
    )
