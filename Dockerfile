FROM ghcr.io/arduino/app-bricks/python-apps-base:0.10.1
USER root

# git is needed for pip install git+https://
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install all three libraries as proper packages.
# STT requires sunfounder_tts (for AudioPlayer) and robot_shield (for I2C/button).
RUN pip install --no-cache-dir \
    git+https://github.com/sunfounder/robot_shield.git@main \
    "sunfounder-stt[all] @ git+https://github.com/sunfounder/sunfounder_stt.git@main" \
    git+https://github.com/sunfounder/sunfounder_tts.git@main

RUN mkdir -p /app/.cache && chown 1000:1000 /app/.cache
USER 1000

ENTRYPOINT ["/bin/sleep"]
CMD ["infinity"]
