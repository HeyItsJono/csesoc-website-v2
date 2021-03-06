from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from app.sponsors.models import Sponsor
from datetime import date

def sponsors(request):
   sponsors = Sponsor.objects.order_by('amount_paid').reverse().filter(expiry_date__gte=date.today)
   return render_to_response('sponsors/index.html', {'sponsors': sponsors}, context_instance=RequestContext(request))
