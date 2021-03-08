@echo off
setlocal enabledelayedexpansion

REM ~~ INTENDED FOR BEGINNERS, DEVELOPMENT AND/OR LEARNING PURPOSES ONLY ~~

REM Tested as working in Windows 10 with: python 3.6.8 ; django 3.1.7.
REM All the commands run under the assumption that 'django' and 'python' are already installed on your computer.
REM All the commands reflect the Windows DOS way of proccessing the tutorial commands in an automated process.
REM When required, the escape characters used here are both ^ and %.
REM This batch file could possibly be modified to work in other OS terminal applications.

REM This could be considered as a finished product representing the django intro tutorial.
REM It is highly recommended that you initially go through the whole tutorial on your own.
REM Not absolutely everything is included but the gist of the tutorial has been captured.
REM One changed part of the tutorial here is: polls app -> split into poll1 and poll2 apps (to show multi page creation in a single process).

REM ~~ Access the tutorial here: https://docs.djangoproject.com/en/3.1/intro/tutorial01/ ~~

REM Copy this batch file to your choice of folder (suggestion: create a folder named "Polls").
REM Open command prompt and navigate to that folder. 
REM To start the process below, type the following comand: polls.bat

REM ~ FIRST RUN WILL ATTEMPT TO CREATE THE PROJECT, DIRECTORY STRUCTURE, SETUP DATABASE, CREATE ADMIN ACCOUNT AND RUN THE SERVER
REM ~ SUBSEQUENT RUNS WILL ATTEMPT TO RUN THE SERVER (if mysite folder is detected)

if exist mysite\ (
  echo ------------------------------
  echo  mysite folder already exists
  echo  attempting to run the server
  echo ------------------------------
  goto RunServer
)

echo -------------------------------------
echo  attempting to create django project
echo -------------------------------------

django-admin startproject mysite

cd mysite

python manage.py startapp poll1
python manage.py startapp poll2

REM -------------------------------------------------------------------------------------------------------------------------

cd poll1

echo. >> views.py
echo from django.http import HttpResponseRedirect >> views.py
echo from django.utils import timezone >> views.py
echo from .models import Question, Choice >> views.py
echo from django.shortcuts import get_object_or_404, render >> views.py
echo from django.urls import reverse >> views.py
echo from django.views import generic >> views.py
echo. >> views.py
echo class IndexView(generic.ListView): >> views.py
echo     template_name = 'poll1/index.html' >> views.py
echo     context_object_name = 'latest_question_list' >> views.py
echo. >> views.py
echo     def get_queryset(self): >> views.py
echo         ^"^"^" >> views.py
echo         Return the last five published questions (not including those >> views.py
echo         set to be published in the future). >> views.py
echo         ^"^"^" >> views.py
echo         return Question.objects.filter(pub_date__lte=timezone.now()).order_by('-pub_date')[:5] >> views.py
echo. >> views.py
echo class DetailView(generic.DetailView): >> views.py
echo     model = Question >> views.py
echo     template_name = 'poll1/detail.html' >> views.py
echo. >> views.py
echo     def get_queryset(self): >> views.py
echo         ^"^"^" >> views.py
echo         Excludes any questions that aren't published yet. >> views.py
echo         ^"^"^" >> views.py
echo         return Question.objects.filter(pub_date__lte=timezone.now()) >> views.py
echo. >> views.py
echo class ResultsView(generic.DetailView): >> views.py
echo     model = Question >> views.py
echo     template_name = 'poll1/results.html' >> views.py
echo. >> views.py
echo def vote(request, question_id): >> views.py
echo     question = get_object_or_404(Question, pk=question_id) >> views.py
echo     try: >> views.py
echo         selected_choice = question.choice_set.get(pk=request.POST['choice']) >> views.py
echo     except (KeyError, Choice.DoesNotExist): >> views.py
echo         # Redisplay the question voting form. >> views.py
echo         return render(request, 'poll1/detail.html', { >> views.py
echo             'question': question, >> views.py
echo             'error_message': "You didn't select a choice.", >> views.py
echo         }) >> views.py
echo     else: >> views.py
echo         selected_choice.votes += 1 >> views.py
echo         selected_choice.save() >> views.py
echo         # Always return an HttpResponseRedirect after successfully dealing >> views.py
echo         # with POST data. This prevents data from being posted twice if a >> views.py
echo         # user hits the Back button. >> views.py
echo         return HttpResponseRedirect(reverse('poll1:results', args=(question.id,))) >> views.py

echo from django.urls import path > urls.py
echo from . import views >> urls.py
echo. >> urls.py
echo app_name = 'poll1' >> urls.py
echo urlpatterns = [ >> urls.py
echo     path('', views.IndexView.as_view(), name='index'), >> urls.py
echo     path('^<int:pk^>/', views.DetailView.as_view(), name='detail'), >> urls.py
echo     path('^<int:pk^>/results/', views.ResultsView.as_view(), name='results'), >> urls.py
echo     path('^<int:question_id^>/vote/', views.vote, name='vote'), >> urls.py
echo ] >> urls.py

echo import datetime >> models.py
echo from django.db import models >> models.py
echo from django.utils import timezone >> models.py
echo. >> models.py
echo class Question(models.Model): >> models.py
echo    question_text = models.CharField(max_length=200) >> models.py
echo    pub_date = models.DateTimeField('date published') >> models.py
echo. >> models.py
echo    def __str__(self): >> models.py
echo        return self.question_text >> models.py
echo. >> models.py
echo    def was_published_recently(self): >> models.py
echo        now = timezone.now() >> models.py
echo        return now - datetime.timedelta(days=1) ^<= self.pub_date ^<= now >> models.py
echo. >> models.py
echo    was_published_recently.admin_order_field = 'pub_date' >> models.py
echo    was_published_recently.boolean = True >> models.py
echo    was_published_recently.short_description = 'Published recently?' >> models.py
echo. >> models.py
echo class Choice(models.Model): >> models.py
echo    question = models.ForeignKey(Question, on_delete=models.CASCADE) >> models.py
echo    choice_text = models.CharField(max_length=200) >> models.py
echo    votes = models.IntegerField(default=0) >> models.py
echo. >> models.py
echo    def __str__(self): >> models.py
echo        return self.choice_text >> models.py

echo from django.contrib import admin >> admin.py
echo from .models import Question, Choice >> admin.py
echo. >> admin.py
echo class ChoiceInline(admin.TabularInline): >> admin.py
echo     model = Choice >> admin.py
echo     extra = 3 >> admin.py
echo. >> admin.py
echo class QuestionAdmin(admin.ModelAdmin): >> admin.py
echo     fieldsets = [ >> admin.py
echo         (None,               {'fields': ['question_text']}), >> admin.py
echo         ('Date information', {'fields': ['pub_date']}), >> admin.py
echo     ] >> admin.py
echo     list_display = ('question_text', 'pub_date', 'was_published_recently') >> admin.py
echo     inlines = [ChoiceInline] >> admin.py
echo     list_filter = ['pub_date'] >> admin.py
echo     search_fields = ['question_text'] >> admin.py
echo. >> admin.py
echo admin.site.register(Question, QuestionAdmin) >> admin.py
echo admin.site.register(Choice) >> admin.py

mkdir templates
cd templates
mkdir poll1
cd poll1

echo ^<^!DOCTYPE html^> > index.html
echo ^<html^> >> index.html
echo   ^<head^> >> index.html
echo     {%% load static %%} >> index.html
echo     ^<link rel="stylesheet" type="text/css" href="{%% static 'poll1/style.css' %%}"^> >> index.html
echo     ^<meta charset="utf-8"^> >> index.html
echo     ^<title^>Poll 1^</title^> >> index.html
echo   ^</head^> >> index.html
echo   ^<body^> >> index.html
echo     ^<p^>^<h2^>Poll 1 Questions^</h2^>^</p^> >> index.html
echo     {%% if latest_question_list %%} >> index.html
echo         ^<ul^> >> index.html
echo         {%% for question in latest_question_list %%} >> index.html
echo             ^<li^>^<a href="{%% url 'poll1:detail' question.id %%}"^>{{ question.question_text }}^</a^>^</li^> >> index.html
echo         {%% endfor %%} >> index.html
echo         ^</ul^> >> index.html
echo     {%% else %%} >> index.html
echo         ^<p^>Poll 1 has no questions available.^</p^> >> index.html
echo     {%% endif %%} >> index.html
echo   ^</body^> >> index.html
echo ^</html^> >> index.html

echo ^<^!DOCTYPE html^> > detail.html
echo ^<html^> >> detail.html
echo   ^<head^> >> detail.html
echo     {%% load static %%} >> detail.html
echo     ^<link rel="stylesheet" type="text/css" href="{%% static 'poll1/style.css' %%}"^> >> detail.html
echo     ^<meta charset="utf-8"^> >> detail.html
echo     ^<title^>Poll 1 Detail^</title^> >> detail.html
echo   ^</head^> >> detail.html
echo   ^<body^> >> detail.html
echo     ^<p^>^<h1^>{{ question.question_text }}^</h1^>^</p^> >> detail.html
echo     {%% if error_message %%}^<p^>^<strong^>{{ error_message }}^</strong^>^</p^>{%% endif %%} >> detail.html
echo     ^<form action="{%% url 'poll1:vote' question.id %%}" method="post"^> >> detail.html
echo       {%% csrf_token %%} >> detail.html
echo       {%% for choice in question.choice_set.all %%} >> detail.html
echo           ^<input type="radio" name="choice" id="choice{{ forloop.counter }}" value="{{ choice.id }}"^> >> detail.html
echo           ^<label for="choice{{ forloop.counter }}"^>{{ choice.choice_text }}^</label^>^<br^> >> detail.html
echo       {%% endfor %%} >> detail.html
echo       ^<p^>^</p^> >> detail.html
echo       ^<input type="submit" value="Vote"^> >> detail.html
echo       ^<p^>^<a href="{%% url 'poll1:index' %%}"^>Back to questions^</a^>^</p^> >> detail.html
echo     ^</form^> >> detail.html
echo   ^</body^> >> detail.html
echo ^</html^> >> detail.html

echo ^<^!DOCTYPE html^> > results.html
echo ^<html^> >> results.html
echo   ^<head^> >> results.html
echo     {%% load static %%} >> results.html
echo     ^<link rel="stylesheet" type="text/css" href="{%% static 'poll1/style.css' %%}"^> >> results.html
echo     ^<meta charset="utf-8"^> >> results.html
echo     ^<title^>Poll 1 Results^</title^> >> results.html
echo   ^</head^> >> results.html
echo   ^<body^> >> results.html
echo     ^<p^>^<h1^>{{ question.question_text }}^</h1^>^</p^> >> results.html
echo     ^<ul^> >> results.html
echo       {%% for choice in question.choice_set.all %%} >> results.html
echo           ^<li^>{{ choice.choice_text }} -- {{ choice.votes }} vote{{ choice.votes^|pluralize }}^</li^> >> results.html
echo       {%% endfor %%} >> results.html
echo     ^</ul^> >> results.html
echo     ^<a href="{%% url 'poll1:detail' question.id %%}"^>Vote again?^</a^> >> results.html
echo     ^<p^>^<a href="{%% url 'poll1:index' %%}"^>Back to questions^</a^>^</p^> >> results.html
echo   ^</body^> >> results.html
echo ^</html^> >> results.html

cd..
cd..

mkdir static
cd static
mkdir poll1
cd poll1

echo li a { color: navy; } > style.css
echo body { background: lime; } >> style.css

cd..
cd..

REM -------------------------------------------------------------------------------------------------------------------------
REM Use this section as a pattern to add any subsequent poll (also see comments to add it to path / INSTALLED_APPS / migration)

cd..
cd poll2

echo. >> views.py
echo from django.http import HttpResponseRedirect >> views.py
echo from django.utils import timezone >> views.py
echo from .models import Question, Choice >> views.py
echo from django.shortcuts import get_object_or_404, render >> views.py
echo from django.urls import reverse >> views.py
echo from django.views import generic >> views.py
echo. >> views.py
echo class IndexView(generic.ListView): >> views.py
echo     template_name = 'poll2/index.html' >> views.py
echo     context_object_name = 'latest_question_list' >> views.py
echo. >> views.py
echo     def get_queryset(self): >> views.py
echo         ^"^"^" >> views.py
echo         Return the last five published questions (not including those >> views.py
echo         set to be published in the future). >> views.py
echo         ^"^"^" >> views.py
echo         return Question.objects.filter(pub_date__lte=timezone.now()).order_by('-pub_date')[:5] >> views.py
echo. >> views.py
echo class DetailView(generic.DetailView): >> views.py
echo     model = Question >> views.py
echo     template_name = 'poll2/detail.html' >> views.py
echo. >> views.py
echo     def get_queryset(self): >> views.py
echo         ^"^"^" >> views.py
echo         Excludes any questions that aren't published yet. >> views.py
echo         ^"^"^" >> views.py
echo         return Question.objects.filter(pub_date__lte=timezone.now()) >> views.py
echo. >> views.py
echo class ResultsView(generic.DetailView): >> views.py
echo     model = Question >> views.py
echo     template_name = 'poll2/results.html' >> views.py
echo. >> views.py
echo def vote(request, question_id): >> views.py
echo     question = get_object_or_404(Question, pk=question_id) >> views.py
echo     try: >> views.py
echo         selected_choice = question.choice_set.get(pk=request.POST['choice']) >> views.py
echo     except (KeyError, Choice.DoesNotExist): >> views.py
echo         # Redisplay the question voting form. >> views.py
echo         return render(request, 'poll2/detail.html', { >> views.py
echo             'question': question, >> views.py
echo             'error_message': "You didn't select a choice.", >> views.py
echo         }) >> views.py
echo     else: >> views.py
echo         selected_choice.votes += 1 >> views.py
echo         selected_choice.save() >> views.py
echo         # Always return an HttpResponseRedirect after successfully dealing >> views.py
echo         # with POST data. This prevents data from being posted twice if a >> views.py
echo         # user hits the Back button. >> views.py
echo         return HttpResponseRedirect(reverse('poll2:results', args=(question.id,))) >> views.py

echo from django.urls import path > urls.py
echo from . import views >> urls.py
echo. >> urls.py
echo app_name = 'poll2' >> urls.py
echo urlpatterns = [ >> urls.py
echo     path('', views.IndexView.as_view(), name='index'), >> urls.py
echo     path('^<int:pk^>/', views.DetailView.as_view(), name='detail'), >> urls.py
echo     path('^<int:pk^>/results/', views.ResultsView.as_view(), name='results'), >> urls.py
echo     path('^<int:question_id^>/vote/', views.vote, name='vote'), >> urls.py
echo ] >> urls.py

echo import datetime >> models.py
echo from django.db import models >> models.py
echo from django.utils import timezone >> models.py
echo. >> models.py
echo class Question(models.Model): >> models.py
echo    question_text = models.CharField(max_length=200) >> models.py
echo    pub_date = models.DateTimeField('date published') >> models.py
echo. >> models.py
echo    def __str__(self): >> models.py
echo        return self.question_text >> models.py
echo. >> models.py
echo    def was_published_recently(self): >> models.py
echo        now = timezone.now() >> models.py
echo        return now - datetime.timedelta(days=1) ^<= self.pub_date ^<= now >> models.py
echo. >> models.py
echo    was_published_recently.admin_order_field = 'pub_date' >> models.py
echo    was_published_recently.boolean = True >> models.py
echo    was_published_recently.short_description = 'Published recently?' >> models.py
echo. >> models.py
echo class Choice(models.Model): >> models.py
echo    question = models.ForeignKey(Question, on_delete=models.CASCADE) >> models.py
echo    choice_text = models.CharField(max_length=200) >> models.py
echo    votes = models.IntegerField(default=0) >> models.py
echo. >> models.py
echo    def __str__(self): >> models.py
echo        return self.choice_text >> models.py

echo from django.contrib import admin >> admin.py
echo from .models import Question, Choice >> admin.py
echo. >> admin.py
echo class ChoiceInline(admin.TabularInline): >> admin.py
echo     model = Choice >> admin.py
echo     extra = 3 >> admin.py
echo. >> admin.py
echo class QuestionAdmin(admin.ModelAdmin): >> admin.py
echo     fieldsets = [ >> admin.py
echo         (None,               {'fields': ['question_text']}), >> admin.py
echo         ('Date information', {'fields': ['pub_date']}), >> admin.py
echo     ] >> admin.py
echo     list_display = ('question_text', 'pub_date', 'was_published_recently') >> admin.py
echo     inlines = [ChoiceInline] >> admin.py
echo     list_filter = ['pub_date'] >> admin.py
echo     search_fields = ['question_text'] >> admin.py
echo. >> admin.py
echo admin.site.register(Question, QuestionAdmin) >> admin.py
echo admin.site.register(Choice) >> admin.py

mkdir templates
cd templates
mkdir poll2
cd poll2

echo ^<^!DOCTYPE html^> > index.html
echo ^<html^> >> index.html
echo   ^<head^> >> index.html
echo     {%% load static %%} >> index.html
echo     ^<link rel="stylesheet" type="text/css" href="{%% static 'poll2/style.css' %%}"^> >> index.html
echo     ^<meta charset="utf-8"^> >> index.html
echo     ^<title^>Poll 2^</title^> >> index.html
echo   ^</head^> >> index.html
echo   ^<body^> >> index.html
echo     ^<p^>^<h2^>Poll 2 Questions^</h2^>^</p^> >> index.html
echo     {%% if latest_question_list %%} >> index.html
echo         ^<ul^> >> index.html
echo         {%% for question in latest_question_list %%} >> index.html
echo             ^<li^>^<a href="{%% url 'poll2:detail' question.id %%}"^>{{ question.question_text }}^</a^>^</li^> >> index.html
echo         {%% endfor %%} >> index.html
echo         ^</ul^> >> index.html
echo     {%% else %%} >> index.html
echo         ^<p^>Poll 2 has no questions available.^</p^> >> index.html
echo     {%% endif %%} >> index.html
echo   ^</body^> >> index.html
echo ^</html^> >> index.html

echo ^<^!DOCTYPE html^> > detail.html
echo ^<html^> >> detail.html
echo   ^<head^> >> detail.html
echo     {%% load static %%} >> detail.html
echo     ^<link rel="stylesheet" type="text/css" href="{%% static 'poll2/style.css' %%}"^> >> detail.html
echo     ^<meta charset="utf-8"^> >> detail.html
echo     ^<title^>Poll 2 Detail^</title^> >> detail.html
echo   ^</head^> >> detail.html
echo   ^<body^> >> detail.html
echo     ^<p^>^<h1^>{{ question.question_text }}^</h1^>^</p^> >> detail.html
echo     {%% if error_message %%}^<p^>^<strong^>{{ error_message }}^</strong^>^</p^>{%% endif %%} >> detail.html
echo     ^<form action="{%% url 'poll2:vote' question.id %%}" method="post"^> >> detail.html
echo       {%% csrf_token %%} >> detail.html
echo       {%% for choice in question.choice_set.all %%} >> detail.html
echo           ^<input type="radio" name="choice" id="choice{{ forloop.counter }}" value="{{ choice.id }}"^> >> detail.html
echo           ^<label for="choice{{ forloop.counter }}"^>{{ choice.choice_text }}^</label^>^<br^> >> detail.html
echo       {%% endfor %%} >> detail.html
echo       ^<p^>^</p^> >> detail.html
echo       ^<input type="submit" value="Vote"^> >> detail.html
echo       ^<p^>^<a href="{%% url 'poll2:index' %%}"^>Back to questions^</a^>^</p^> >> detail.html
echo     ^</form^> >> detail.html
echo   ^</body^> >> detail.html
echo ^</html^> >> detail.html

echo ^<^!DOCTYPE html^> > results.html
echo ^<html^> >> results.html
echo   ^<head^> >> results.html
echo     {%% load static %%} >> results.html
echo     ^<link rel="stylesheet" type="text/css" href="{%% static 'poll2/style.css' %%}"^> >> results.html
echo     ^<meta charset="utf-8"^> >> results.html
echo     ^<title^>Poll 2 Results^</title^> >> results.html
echo   ^</head^> >> results.html
echo   ^<body^> >> results.html
echo     ^<p^>^<h1^>{{ question.question_text }}^</h1^>^</p^> >> results.html
echo     ^<ul^> >> results.html
echo       {%% for choice in question.choice_set.all %%} >> results.html
echo           ^<li^>{{ choice.choice_text }} -- {{ choice.votes }} vote{{ choice.votes^|pluralize }}^</li^> >> results.html
echo       {%% endfor %%} >> results.html
echo     ^</ul^> >> results.html
echo     ^<a href="{%% url 'poll2:detail' question.id %%}"^>Vote again?^</a^> >> results.html
echo     ^<p^>^<a href="{%% url 'poll2:index' %%}"^>Back to questions^</a^>^</p^> >> results.html
echo   ^</body^> >> results.html
echo ^</html^> >> results.html

cd..
cd..

mkdir static
cd static
mkdir poll2
cd poll2

echo li a { color: maroon; } > style.css
echo body { background: cyan; } >> style.css

cd..
cd..

REM -------------------------------------------------------------------------------------------------------------------------
REM Add a path for any subsequently added poll here.

cd..
cd mysite

echo from django.urls import include >> urls.py
echo urlpatterns = [path('poll1/', include('poll1.urls')),path('poll2/', include('poll2.urls')),path('admin/', admin.site.urls),] >> urls.py

REM -------------------------------------------------------------------------------------------------------------------------
REM Add a line for any subsequently added poll to the INSTALLED_APPS section.
REM Optionally change the TIME_ZONE value.

echo. > temp.txt

set origfile=settings.py
set tempfile=temp.txt

for %%a in (%origfile%) do (
    (for /f "usebackq delims=" %%h in ("%%a") do (
        if "%%h" equ "TIME_ZONE = 'UTC'" (
            echo TIME_ZONE = 'EST'
        ) else (
            echo %%h
            if "%%h" equ "INSTALLED_APPS = [" (
                echo     'poll1.apps.Poll1Config',
                echo     'poll2.apps.Poll2Config',
            )
        )
    ))>"%tempfile%"
)

COPY /Y %tempfile% %origfile% >NUL
DEL %tempfile%

REM -------------------------------------------------------------------------------------------------------------------------
REM Add any subsequently added poll to this section.

cd..

python manage.py migrate

python manage.py makemigrations poll1
python manage.py makemigrations poll2

python manage.py sqlmigrate poll1 0001
python manage.py sqlmigrate poll2 0001

python manage.py migrate

REM -------------------------------------------------------------------------------------------------------------------------

echo --------------------------------------------------------------------------
echo Create superuser as the admin for the site http://127.0.0.1:8000/admin/
echo --------------------------------------------------------------------------

python manage.py createsuperuser

REM -------------------------------------------------------------------------------------------------------------------------
REM Show usage messages

echo --------------------------------------------------------------------------
echo You can access the following pages from your browser:
echo  http://127.0.0.1:8000/admin/  - use the admin account you just created
echo  http://127.0.0.1:8000/poll1/
echo  http://127.0.0.1:8000/poll2/
echo --------------------------------------------------------------------------
echo To restart the server, just run this batch file again.
echo.
echo Alternatively, navigate to the outer mysite by typing "cd mysite".
echo Run the server by typing "python manage.py runserver".
echo --------------------------------------------------------------------------

python manage.py runserver

goto End

:RunServer
cd mysite
if exist manage.py (
  python manage.py runserver
)

:End