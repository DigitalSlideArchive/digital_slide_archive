---
layout: home

# Banner Content
# =================================
title: Harness the full potential of your digital pathology data
subtitle: A containerized web-based platform for the analysis, visualization, management and annotation of whole-slide digital pathology imaging data

hero_image: assets/img/dsa_hero.jpg

hero_buttons:
  - link_text: View Demo
    link: https://demo.kitware.com/histomicstk/histomicstk

  - link_text: View on GitHub
    link: https://github.com/DigitalSlideArchive

  - link_text: Installation
    link: https://github.com/DigitalSlideArchive/digital_slide_archive/blob/master/ansible/README.rst

# What is DSA Section
# =================================
about_title: What is DSA?
about_text: The Digital Slide Archive (DSA) is a platform that provides the ability to store, manage, visualize and annotate large imaging data sets. The DSA consists of an analysis toolkit (HistomicsTK), an interface to visualize slides and manage annotations (HistomicsUI), a database layer (using Mongo), and a web-server that provides a rich API and data management tools (using Girder). This system can

# Capabilities of DSA
about_list:
  - list_item: Organize images from a variety of assetstores, such as local files systems and S3.
  - list_item: Provide user access controls.
  - list_item: Image annotation and review.
  - list_item: Run algorithms on all or parts of images.

# Resource links
about_resources_title: Resources

about_system_diagram: assets/img/system-diagrams/system-diagram.svg
about_system_diagram_caption: System Overview
about_system_link: system-overview

about_resources:
  - name: Gitter
    link: https://gitter.im/DigitalSlideArchive/HistomicsTK
    icon: fab fa-gitter

  - name: Discourse
    link: https://discourse.girder.org/c/histomicstk
    icon: fab fa-discourse

  - name: Jupyter
    link: https://digitalslidearchive.github.io/HistomicsTK/examples.html
    icon: fas fa-book

  - name: Youtube
    link: https://www.youtube.com/channel/UCe9RJmSdEJLTWkRhSOIVAlg
    icon: fab fa-youtube

# Platforms Content
# =================================
platforms:
  # HistomicsUI
  - title: HistomicsUI
    description: HistomicsUI is a web-based application for examining, annotating, and processing histology images to extract both low and high level features (e.g. cellular structure, feature types).
    docs_url: https://github.com/DigitalSlideArchive/HistomicsUI/blob/master/README.rst
    github_url: https://github.com/DigitalSlideArchive/HistomicsUI
    screenshot: assets/img/histomicsui_screenshot.png
    features:
      - name: Secure Data Management
        description: The DSA provides fine-grained user or role-based access to datasets, images & metadata, and annotations. Amazon S3 hosting supported.
        icon: assets/img/feature-icons/icon-secure_data_management.svg

      - name: RESTful APIs
        description: A rich API allows programmatic control over users, data, annotations, and algorithms, enabling automation of DSA tasks and integration with other tools and platforms.
        icon: assets/img/feature-icons/icon-restful_apis.svg

      - name: Visualization and Annotation
        description: An optimized user interface provides fluid exploration of large whole-slide images and tools for efficient generation of image markups.
        icon: assets/img/feature-icons/icon-visualization_annotation.svg

      - name: Execution Engine
        description: Girder provides distributed execution and monitoring of algorithm and analytics jobs.
        icon: assets/img/feature-icons/icon-execution_engine.svg

      - name: Broad Support for Histology Image Formats
        description: A wide variety of tiled image formats are supported, including tiff, svs, and jp2. Images can be retiled automatically as needed for processing algorithms. Additional formats can be added with a pluggable Python interface.
        icon: assets/img/feature-icons/icon-history_image_formats-primary.svg

  # HistomicsTK
  - title: HistomicsTK
    description: HistomicsTK is a Python image-processing toolkit for quantitative analysis of whole-slide digital pathology images.
    docs_url: https://digitalslidearchive.github.io/HistomicsTK/
    github_url: https://github.com/DigitalSlideArchive/HistomicsTK
    screenshot: assets/img/histomicstk_screenshot.png
    features:
      - name: Preprocessing
        description: HistomicsTK provides color normalization and deconvolution operations to improve the robustness of analytic pipelines.
        icon: assets/img/feature-icons/icon-preprocessing.svg

      - name: Object Detection and Segmentation
        description: HistomicsTK contains a number of classical image analysis and machine-learning based algorithms for object detection and segmentation of subcellular structures and tissues.
        icon: assets/img/feature-icons/icon-object_detection.svg

      - name: Feature Extraction and Predictive Modeling
        description: Object and patch-level features describing shape, texture, and color can be used to build machine-learning models.
        icon: assets/img/feature-icons/icon-feature_extraction.svg

      - name: Extensibility
        description: Users can integrate their custom algorithms through a containerization process that auto-generates DSA user-interfaces.
        icon: assets/img/feature-icons/icon-extensibility.svg

      - name: Broad Support for Histology Image Formats
        description: The same wide variety of histology images that can be viewed can be used with any processing algorithms. Sub-images can be processed at custom tile sizes and magnifications as needed.
        icon: assets/img/feature-icons/icon-history_image_formats-secondary.svg

# Callouts Section
# =================================
callouts:
  - heading: Demos & Examples
    link: demos-examples
    link_text: View Demos
    image: assets/img/home-callouts/demos_examples.jpg

  - heading: Success Stories
    link: success-stories
    link_text: View Stories
    image: assets/img/home-callouts/success_stories.jpg

  - heading: Papers & Publications
    link: papers-publications
    link_text: Read Papers
    image: assets/img/home-callouts/papers_publications.jpg

# Collaborators Section
# =================================
organizations:
  - name: Feinberg School of Medicine - Northwestern University
    logo: assets/img/collaborators/logo-feinberg_school_of_medicine.png
    link: https://www.feinberg.northwestern.edu/
    members:
      - name: Lee A.D. Cooper, PhD
        role: HistomicsTK Lead
        title: Associate Professor of Pathology
        headshot: assets/img/collaborators/headshot-lee_cooper.jpg
        link: https://www.feinberg.northwestern.edu/faculty-profiles/az/profile.html?xid=44206

  - name: Emory University - School of Medicine
    logo: assets/img/collaborators/logo-emory_school_of_medicine.png
    link: https://www.med.emory.edu/
    members:
      - name: David A. Gutman, MD, PhD
        role: Digital Slide Archive Lead
        title: Associate Professor of Neurology
        headshot: assets/img/collaborators/headshot-david_gutman.jpg
        link: https://winshipcancer.emory.edu/bios/faculty/gutman-david.html

  - name: Kitware, Inc.
    logo: assets/img/collaborators/logo-kitware.png
    link: https://www.kitware.com/
    members:
      - name: David Manthey
        role: Software Engineering & Deployment
        title: Staff R&D Engineer
        headshot: assets/img/collaborators/headshot-david_manthey.jpg
        link: https://www.kitware.com/david-manthey/
---
