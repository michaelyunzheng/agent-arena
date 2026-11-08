FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# Catan does not use Yarn. Remove its inherited apt source, whose stale
# signing key can block installation of the desktop feature.
USER root
RUN rm -f /etc/apt/sources.list.d/yarn.list
