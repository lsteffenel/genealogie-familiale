from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils import timezone

from .models import EditProposal, Event, Media, Person, Profile, Union


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email")


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
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
    list_display = ("title", "person", "event", "google_photo_media_item_id", "created_at")
    search_fields = ("title",)


@admin.register(EditProposal)
class EditProposalAdmin(admin.ModelAdmin):
    list_display = ("id", "content_type", "object_id", "proposed_by", "status", "created_at")
    list_filter = ("status", "content_type")
    readonly_fields = ("created_at", "reviewed_at")
    actions = ("approve_proposals", "reject_proposals")

    @admin.action(description="Approuver les propositions sélectionnées")
    def approve_proposals(self, request, queryset):
        count = 0
        for proposal in queryset.filter(status="pending"):
            proposal.apply(request.user)
            count += 1
        self.message_user(request, f"{count} proposition(s) approuvée(s).")

    @admin.action(description="Rejeter les propositions sélectionnées")
    def reject_proposals(self, request, queryset):
        count = queryset.filter(status="pending").update(
            status="rejected", reviewed_by=request.user, reviewed_at=timezone.now()
        )
        self.message_user(request, f"{count} proposition(s) rejetée(s).")
