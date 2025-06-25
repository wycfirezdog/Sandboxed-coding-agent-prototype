FROM python:3.10-slim

LABEL maintainer="Sandboxed Agent <maintainers@example.com>"
ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# ---------- System packages ----------
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        xvfb x11vnc xauth xinit xdotool \
        wget ca-certificates git supervisor \
        && rm -rf /var/lib/apt/lists/*

# ---------- Install noVNC ----------
RUN mkdir -p /opt/novnc && \
    wget -qO- https://github.com/novnc/noVNC/archive/refs/tags/v1.4.0.tar.gz | tar xz --strip 1 -C /opt/novnc && \
    ln -s /opt/novnc/utils/novnc_proxy /usr/local/bin/novnc_proxy

# ---------- Python deps ----------
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Copy source ----------
COPY src ./src

# ---------- Supervisor configuration ----------
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 8000 5901 6080 8888

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"] 