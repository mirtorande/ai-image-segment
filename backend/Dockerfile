FROM pytorch/pytorch:2.6.0-cuda12.6-cudnn9-devel
WORKDIR /app
COPY . /app
#RUN apt-get update && apt-get install -y libgl1-mesa-glx
RUN pip install -r requirements.txt
EXPOSE 80
CMD ["fastapi", "dev", "--host", "0.0.0.0", "--port", "80", "main.py"]