# GitHub Pages Landing Page
This website uses the [Bulma Clean Theme](https://github.com/chrisrhymes/bulma-clean-theme) for Jekyll.

### Running the site locally
1. Open a terminal and clone the [digital_slide_archive](https://github.com/DigitalSlideArchive/digital_slide_archive) repo
1. Navigate to the docs folder – `cd docs`
1. Run the command `bundle exec jekyll serve`
    * You may need to run `bundle install && bundle update` if this step fails. Once that is done, repeat step 3.

**NOTE:** You will see `Invalid theme folder: _sass` when you serve the site. It has to do with the use of the Bulma Clean Theme as a remote_theme in the `config.yml`. `remote_theme: chrisrhymes/bulma-clean-theme` is used instead of `theme: bulma-clean-theme` in order to make the theme play nicely with GitHub pages. Because of this, please ignore the Invalid theme folder warning.
