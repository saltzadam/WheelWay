FROM wheelway:base

WORKDIR /usr/src/
COPY . .

EXPOSE 8050

# make everything use conda environment

# ENV PATH /opt/conda/envs/wheelway/bin:$PATH
SHELL ["/opt/conda/bin/conda", "run", "-n", "wheelway", "/bin/bash", "-c"]

RUN echo "Make sure dash is installed"
run python -c "import dash"

#RUN /bin/bash -c "source activate wheelway"
#CMD ["conda", "list"]

ENTRYPOINT ["/opt/conda/bin/conda", "run", "-n", "wheelway", "python", "app/app.py"]
