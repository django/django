from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    # path("<int:pk>/", views.project_detail, name="project_detail"),
    #path('', views.hello_world, name='hello_world'),
    path('/project_detail', views.project_detail, name='project_detail'),
    # path('/p_', views.p_, name='p_'),
    path('/p_ro_website', views.p_ro_website, name='p_ro_website'),
    path('/p_ro_ftux', views.p_ro_ftux, name='p_ro_ftux'),
    path('/p_codepen', views.p_codepen, name='p_codepen'),
    path('/p_rev_design', views.p_rev_design, name='p_rev_design'),
    path('/p_rev_email', views.p_rev_email, name='p_rev_email'),
    path('/p_rev_mktg', views.p_rev_mktg, name='p_rev_mktg'),
    path('/p_print', views.p_print, name='p_print'),
    path('/p_portfolio', views.p_portfolio, name='p_portfolio'),

]
