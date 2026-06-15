FROM ghcr.io/arduino/app-bricks/python-apps-base:0.10.1
USER root

# Install all three libraries as proper packages.
# STT requires sunfounder_tts (for AudioPlayer) and robot_shield (for I2C/button).
COPY python-libraries/robot_shield /app/python-libraries/robot_shield
COPY python-libraries/sunfounder_stt /app/python-libraries/sunfounder_stt
COPY python-libraries/sunfounder_tts /app/python-libraries/sunfounder_tts
RUN pip install --no-cache-dir \
    /app/python-libraries/robot_shield \
    "/app/python-libraries/sunfounder_stt[all]" \
    /app/python-libraries/sunfounder_tts

RUN mkdir -p /app/.cache && chown 1000:1000 /app/.cache
USER 1000

ENTRYPOINT ["/bin/sleep"]
CMD ["infinity"]
