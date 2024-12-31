FROM python:3.10-buster
EXPOSE 8000
WORKDIR /app 
COPY . /app
RUN python -m pip install .
RUN django-admin startproject allyapp
ENTRYPOINT ["python3"] 
CMD ["allyapp/manage.py", "runserver", "0.0.0.0:8000"]