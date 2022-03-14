from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    # path("<int:pk>/", views.project_detail, name="project_detail"),
    #path('', views.hello_world, name='hello_world'),
    path('/project_detail', views.project_detail, name='project_detail'),
    path('/p_email_strategy', views.p_email_strategy, name='p_email_strategy'),

]
