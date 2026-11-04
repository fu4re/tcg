# The E1 "second machine": a clean Ubuntu 24.04 that holds only the verifier
# (setup.sh, requirements.lock, tools/specgame_core.py, tools/verify.py,
# schemas/, protocol.json) and the pinned toolchain setup.sh installs. The
# bundle is mounted read-only at /bundle at run time; nothing else of the
# workspace is ever in the image or the container. Build context: the staging
# directory run_isolated.sh creates (only the files above), never specgame/.
FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852

ENV DEBIAN_FRONTEND=noninteractive LC_ALL=C.UTF-8
# setup.sh's apt prerequisites, installed here as root (the image has no sudo;
# setup.sh then finds them present and never calls sudo).
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl unzip python3.12 python3.12-venv \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/specgame
# Toolchain first (pinned sha256 for solc, z3 and the pyrevm wheel; setup.sh
# refuses any other bytes), so a change to the verifier does not re-download it.
COPY setup.sh requirements.lock ./
RUN bash setup.sh

# protocol.json only: the frozen values the verifier compares. protocol.md is
# prose; a bundle records its hash but the verifier never needs the file.
COPY protocol.json ./
# Subject profiles (pinned by protocol.json): the pools, encoding and observation.
COPY subjects/ subjects/
COPY schemas/ schemas/
COPY tools/specgame_core.py tools/verify.py tools/

RUN useradd --create-home --shell /usr/sbin/nologin verifier
USER verifier
ENTRYPOINT ["/opt/specgame/.venv/bin/python", "-I", "-B", "/opt/specgame/tools/verify.py", "/bundle"]
