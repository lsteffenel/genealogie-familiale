from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from .models import EditProposal, Event, Media, Person, Profile, ProposalStatus, SiteConfiguration, Union


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "person")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email",
                     "person__first_name", "person__last_name")


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)

    def save_formset(self, request, form, formset, change):
        # Le signal post_save crée déjà un Profile pour chaque nouvel
        # utilisateur : réutiliser cette ligne au lieu d'en insérer une seconde
        # (sinon IntegrityError sur la contrainte unique user_id).
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, Profile) and instance.pk is None:
                existing = Profile.objects.filter(user=form.instance).first()
                if existing is not None:
                    instance.pk = existing.pk
            instance.save()
        formset.save_m2m()


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    change_list_template = "admin/genealogy/person/change_list.html"
    list_display = ("first_name", "last_name", "birth_date", "death_date", "gedcom_id")
    search_fields = ("first_name", "last_name", "gedcom_id")
    list_filter = ("gender",)


@admin.register(Union)
class UnionAdmin(admin.ModelAdmin):
    list_display = ("partner_a", "partner_b", "union_type", "date", "place")
    search_fields = ("partner_a__first_name", "partner_a__last_name",
                     "partner_b__first_name", "partner_b__last_name")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "person", "date", "place")
    list_filter = ("event_type",)
    search_fields = ("title", "person__first_name", "person__last_name")


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ("title", "person", "event", "created_at")
    search_fields = ("title",)


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {"fields": ("default_tree_root",)}),
        (gettext_lazy("Bandeaux HTML"), {"fields": ("home_page_html", "persons_page_html")}),
    )

    def has_add_permission(self, request):
        return not SiteConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class ProposalStatusFilter(admin.SimpleListFilter):
    title = gettext_lazy("Statut")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return [
            ("pending", _("En attente")),
            ("approved", _("Approuvées")),
            ("rejected", _("Rejetées")),
            ("all", _("Toutes")),
        ]

    def queryset(self, request, queryset):
        value = self.value() or ProposalStatus.PENDING
        if value != "all":
            queryset = queryset.filter(status=value)
        return queryset


@admin.register(EditProposal)
class EditProposalAdmin(admin.ModelAdmin):
    list_display = ("id", "quick_approve", "content_type", "object_id", "proposed_by", "status", "created_at")
    list_filter = (ProposalStatusFilter, "content_type")
    readonly_fields = ("created_at", "reviewed_at")
    actions = ("approve_proposals", "reject_proposals")

    def changelist_view(self, request, extra_context=None):
        self._request = request
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description="✅", ordering="status")
    def quick_approve(self, obj):
        if obj.status != ProposalStatus.PENDING or not hasattr(self, "_request"):
            return ""
        url = reverse("admin:genealogy_editproposal_approve", args=[obj.pk])
        return format_html(
            '<form method="post" action="{}" style="display:inline;margin:0">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
            '<button type="submit" class="button" title="{}">✅</button></form>',
            url,
            get_token(self._request),
            _("Approuver et appliquer"),
        )

    def get_urls(self):
        custom_urls = [
            path(
                "<int:pk>/approve/",
                self.admin_site.admin_view(self.approve_view),
                name="genealogy_editproposal_approve",
            )
        ]
        return custom_urls + super().get_urls()

    def approve_view(self, request, pk):
        proposal = get_object_or_404(EditProposal, pk=pk)
        if request.method == "POST":
            if proposal.status == ProposalStatus.PENDING:
                try:
                    proposal.apply(request.user)
                    self.message_user(
                        request,
                        _("Proposition #%(pk)s approuvée et appliquée.") % {"pk": pk},
                        messages.SUCCESS,
                    )
                except Exception as exc:
                    self.message_user(
                        request,
                        _("Échec de l'application : %(exc)s") % {"exc": exc},
                        messages.ERROR,
                    )
            else:
                self.message_user(
                    request,
                    _("Seule une proposition en attente peut être approuvée."),
                    messages.WARNING,
                )
        return redirect("admin:genealogy_editproposal_changelist")

    @admin.action(description=gettext_lazy("Approuver les propositions sélectionnées"))
    def approve_proposals(self, request, queryset):
        count = 0
        for proposal in queryset.filter(status="pending"):
            proposal.apply(request.user)
            count += 1
        self.message_user(request, _("%(count)s proposition(s) approuvée(s).") % {"count": count})

    @admin.action(description=gettext_lazy("Rejeter les propositions sélectionnées"))
    def reject_proposals(self, request, queryset):
        count = queryset.filter(status="pending").update(
            status="rejected", reviewed_by=request.user, reviewed_at=timezone.now()
        )
        self.message_user(request, _("%(count)s proposition(s) rejetée(s).") % {"count": count})
