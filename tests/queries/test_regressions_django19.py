from django.test import TestCase

from .models import Job, JobResponsibilities, Responsibility


class TestTicket26092(TestCase):
    def test(self):
        p = Job.objects.create(name='programming')
        m = Job.objects.create(name='management')
        mc = Responsibility.objects.create(description='Making coffee')
        dc = Responsibility.objects.create(description='Drinking coffee')
        JobResponsibilities(responsibility=dc, job=p, order=2).save()
        JobResponsibilities(responsibility=mc, job=p, order=1).save()
        JobResponsibilities(responsibility=dc, job=m, order=1).save()
        JobResponsibilities(responsibility=mc, job=m, order=2).save()
        self.assertQuerysetEqual(dc.jobs.order_by('job_to_responsibility'), [m, p], lambda x: x)
        self.assertQuerysetEqual(mc.jobs.order_by('job_to_responsibility'), [p, m], lambda x: x)
