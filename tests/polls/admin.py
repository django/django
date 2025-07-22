from django.contrib import admin

from .models import Question


class QuestionAdmin(admin.ModelAdmin):
    list_display = ["question_text", "pub_date", "was_published_recently"]
    list_filter = ["pub_date"]


admin.site.register(Question, QuestionAdmin)
