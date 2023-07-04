from django.urls import path

urlpatterns = [
    path("beginning-with/<angle_bracket", lambda x: x),
    path("ending-with/angle_bracket>", lambda x: x),
    path("closed_angle>/x/<opened_angle", lambda x: x),
    path("<mixed>angle_bracket>", lambda x: x),
]
