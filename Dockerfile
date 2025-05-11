FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

VOLUME /src
WORKDIR /src

COPY ./requirements/base.txt /src/requirements.txt
# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project to the container
COPY ./app /src/app
#COPY .env /src/app

# Expose port 80
EXPOSE 80

# Run the app
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "80"]