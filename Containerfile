FROM fedora:44
RUN dnf -y install livecd-tools spin-kickstarts pykickstart rpm-build createrepo_c \
    gcc-c++ cmake ninja-build qt6-qtbase-devel qt6-qtdeclarative-devel qt6-qtsvg-devel \
    git rsync findutils tar gzip sudo && dnf clean all
WORKDIR /workspace
CMD ["bash"]
