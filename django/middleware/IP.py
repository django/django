from django.contrib.auth.models import IPBlackList
from django.utils.deprecation import MiddlewareMixin


class IPMiddleware(MiddlewareMixin):
	"""
	Security check used for checking spam or dangerous users or requests,
	which trys to Brute Force login or DOS/DDOS attack (& etc) on server more than 10 times.
	
	Using this can make response bit slower for simple views but for views
	that has heavy calculations (for example get larg data from database
	and serializig them & etc) make response faster and prevents
	unnecessary works on server.
	"""

	def process_request(self, request):
		ip = self.get_client_ip(request=request)

		if IPBlackList.object.is_blocked(ip=ip): # Prevent User if is blocked
			from django.http import HttpResponseForbidden
			from django.utils.translation import gettext_lazy as _

			return HttpResponseForbidden(_("""
			You are not allowed to see website, this will happen when user trying to send dangerous request.
			"""))

		
		request.user.ip_address = ip 
	
		return # return None in case of a valid request

	

	def get_client_ip(self, request) -> str:
		"""
		Gets User IP address form 'HTTP_X_FORWARDED_FOR' if
		there is no 'HTTP_X_FORWARDED_FOR' gets from 'REMOTE_ADDR'
		
		Note:Its not allways true but can handle some feature.
		"""
		x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
		if x_forwarded_for:
			ip = x_forwarded_for.split(',')[0]
		else:
			ip = request.META.get('REMOTE_ADDR')
		
		return ip




## TODO
# [] Add read from cache for faster response
# [] If db updated update cache
