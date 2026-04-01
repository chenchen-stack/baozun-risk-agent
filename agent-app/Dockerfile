FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py server.py ./
COPY static ./static
RUN mkdir -p reports

ENV PYTHONUNBUFFERED=1
# 云平台（Render / Railway / 部分 K8s）会注入 PORT；本地默认 8800
ENV PORT=8800

EXPOSE 8800

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8800}"]
