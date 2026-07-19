FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \ 
    && sed -i 's/plugins.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources


# 安装系统依赖 + Redis 客户端工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    redis-tools \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /tests

# 默认执行 pytest
ENTRYPOINT ["pytest"]
CMD ["-v", "--tb=short"]
