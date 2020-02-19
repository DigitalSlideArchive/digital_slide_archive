---
layout: home

# Banner Content
# =================================
title: Harness the full potential of your digital pathology data
subtitle: A containerized web-based platform for the management, visualization, and annotation of whole-slide digital pathology imaging data

hero_image: ../assets/img/dsa_hero.jpg

hero_buttons:
  - link_text: View Demo
    link: #

  - link_text: Read Docs
    link: #

  - link_text: View on GitHub
    link: #

# What is DSA Section
# =================================
about_title: What is DSA?
about_text: The Digital Slide Archive is a system for working with large microscopy images.

# Capabilities of DSA
about_list:
  - list_item: Organize images from a variety of assetstores, such as local files systems and S3.
  - list_item: Provide user access controls.
  - list_item: Image annotation and review.
  - list_item: Run algorithms on all or parts of images.

# Resource links
about_resources:
  - name: Gitter Channel
    link: #
    icon: ../assets/img/icon_gitter.png

  - name: Discourse Forum
    link: #
    icon: ../assets/img/icon_discourse.png

  - name: JupyterNotebooks
    link: #
    icon: ../assets/img/icon_jupyternb.png

  - name: Youtube Channel
    link: #
    icon: ../assets/img/icon_youtube.png

# Platforms Content
# =================================
platforms:
  # HistomicsUI
  - title: HistomicsUI
    description: Web-based application for examining, annotating, and processing histology images to extract both low and high level features (e.g. cellular structure, feature types).
    docs_url: google.com
    github_url: github.com
    screenshot: ../assets/img/histomicsui_screenshot.png
    features:
      - name: Secure Data Management
        description: The DSA provides fine-grained user or role-based access to datasets, images & metadata, and annotations. Amazon S3 hosting supported.
        icon: ../assets/img/icons/icon-secure_data_management.svg

      - name: RESTful APIs
        description: A rich API allows programmatic control over users, data, annotations, and algorithms, enabling automation of DSA tasks and integration with other tools and platforms.
        icon: ../assets/img/icons/icon-restful_apis.svg

      - name: Visualization and Annotation
        description: An optimized user interface provides fluid exploration of large whole-slide images and tools for efficient generation of image markups.
        icon: ../assets/img/icons/icon-visualization_annotation.svg

      - name: Execution Engine
        description: Girder provides distributed execution and monitoring of algorithm and analytics jobs.
        icon: ../assets/img/icons/icon-execution_engine.svg

      - name: Broad Support for Histology Image Formats
        description: A wide variety of tiled image formats are supported, including tiff, svs, and jp2. Images can be retiled automatically as needed for processing algorithms. Additional formats can be added with a pluggable Python interface.
        icon: ../assets/img/icons/icon-history_image_formats-primary.svg

  # HistomicsTK
  - title: HistomicsTK
    description: HistomicsTK is a Python toolkit based on image processing, for quantitative analysis of whole-slide digital pathology images.
    docs_url: google.com
    github_url: github.com
    screenshot: ../assets/img/histomicstk_screenshot.png
    features:
      - name: Preprocessing and Format Support
        description: HistomicsTK provides color normalization and deconvolution operations to improve the robustness of analytic pipelines. The Large Image plugin gives programmers a convenient interface for reading from whole-slide imaging formats.
        icon: ../assets/img/icons/icon-preprocessing.svg

      - name: Object Detection and Segmentation
        description: HistomicsTK contains a number of classical image analysis and machine-learning based algorithms for object detection and segmentation of subcellular structures and tissues.
        icon: ../assets/img/icons/icon-object_detection.svg

      - name: Feature Extraction and Predictive Modeling
        description: Object and patch-level features describing shape, texture, and color can be used to build machine-learning models.
        icon: ../assets/img/icons/icon-feature_extraction.svg

      - name: Extensibility
        description: Users can integrate their custom algorithms through a containerization process that auto-generates DSA user-interfaces.
        icon: ../assets/img/icons/icon-extensibility.svg

      - name: Broad Support for Histology Image Formats
        description: A wide variety of tiled image formats are supported, including tiff, svs, and jp2. Images can be retiled automatically as needed for processing algorithms. Additional formats can be added with a pluggable Python interface.
        icon: ../assets/img/icons/icon-history_image_formats-secondary.svg

# Callouts Section
# =================================
callouts:
  - heading: Demos & Examples
    link: https://google.com
    link_text: View Demos
    image: ../assets/img/demos_examples.jpg

  - heading: Success Stories
    link: https://google.com
    link_text: View Stories
    image: ../assets/img/success_stories.jpg

  - heading: Papers/Publications
    link: https://google.com
    link_text: Read Papers
    image: ../assets/img/papers_publications.jpg
---
