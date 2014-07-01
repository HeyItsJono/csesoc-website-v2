from django.contrib import admin
from app.camp.campleaders.models import Application
from app.camp.campleaders.models import AwkwardQuestion
from app.camp import campglobals

def make_accepted(modeladmin, request, queryset):
  queryset.update(accepted=True)
make_accepted.short_description = "Accept Leaders"

class ApplicationAdmin(admin.ModelAdmin):
  list_filter = ('year', 'accepted', 'shirt_size', 'payment_status', 'medical_form')
  list_display = ('full_name', 'year','cse_username', 'gender', 'year_or_stage', 'year', 'shirt_size', 'payment_status', 'medical_form', 'accepted')
  actions = [make_accepted, campglobals.mark_depositpaid, campglobals.mark_arcpaid, campglobals.mark_fullpaid, campglobals.mark_medicalyes]
admin.site.register(Application, ApplicationAdmin)
admin.site.register(AwkwardQuestion)

