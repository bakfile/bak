## Dependencies

- [asciinema](https://github.com/asciinema/asciinema)
- [tuterm](https://github.com/veracioux/tuterm)

## Running

To run a non-interactive demo:

```shell
tuterm bak.tut --mode demo
```

To run an interactive tutorial:

```shell
tuterm bak.tut
```

To upload the demo to asciinema and create an SVG animated image:

```
./asciinema_upload_and_create_svg.sh
```

This will copy the asciinema URL to your clipboard and print it to your
terminal. The SVG animation will be created as `./bak_demo.svg`.

**NOTE:**
- You should preview the demo first to verify it, so as to avoid uploading
  content unnecessarily.
- You should run the upload script in a new terminal so it doesn't mess up your
  terminal size
