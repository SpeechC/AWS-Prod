FROM public.ecr.aws/lambda/python:3.13
# Copy function code
COPY src/ /var/task/
# Install deps if you have requirements.txt
# RUN python -m pip install -r /var/task/requirements.txt --target /var/task
CMD ["app.lambda_handler"]
