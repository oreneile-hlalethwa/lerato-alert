from django.contrib import admin

from . import models

admin.site.site_header = 'Lerato Alert admin'
admin.site.site_title = 'Lerato Alert'


@admin.register(models.Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'surname', 'email', 'phone', 'created')
    search_fields = ('name', 'surname', 'email', 'phone')
    exclude = ('token',)


@admin.register(models.Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'member', 'type', 'channel', 'created')
    list_filter = ('type', 'channel')


@admin.register(models.Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('member', 'reason', 'mode', 'lat', 'lng', 'created')
    list_filter = ('mode',)
    readonly_fields = ('recipients', 'delivery')


@admin.register(models.Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reference', 'kind', 'area', 'evidence_count', 'created')
    list_filter = ('kind',)


@admin.register(models.FundApplication)
class FundApplicationAdmin(admin.ModelAdmin):
    list_display = ('member', 'amount', 'status', 'created')
    list_filter = ('status',)
    list_editable = ('status',)


@admin.register(models.Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('reference', 'display_name', 'amount', 'status', 'is_demo', 'created')
    list_filter = ('status', 'is_demo')
    search_fields = ('display_name', 'reference')


@admin.register(models.FundAllocation)
class FundAllocationAdmin(admin.ModelAdmin):
    list_display = ('cause', 'amount', 'is_demo', 'created')
    list_filter = ('cause', 'is_demo')


@admin.register(models.Hotspot)
class HotspotAdmin(admin.ModelAdmin):
    list_display = ('label', 'level', 'category', 'night', 'active', 'is_demo')
    list_filter = ('level', 'category', 'active', 'is_demo')
    list_editable = ('active',)


admin.site.register(models.LessonSuggestion)


@admin.register(models.VaultItem)
class VaultItemAdmin(admin.ModelAdmin):
    # Evidence is sensitive: no file links here, only what exists and when.
    list_display = ('member', 'kind', 'title', 'bytes', 'captured', 'uploaded')
    list_filter = ('kind',)
    fields = readonly_fields = ('member', 'kind', 'title', 'bytes', 'captured', 'uploaded')

    def has_add_permission(self, request):
        return False