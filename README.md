# canvas-public
## Assorted Python scripts used to manage a particularly large higher-ed instance of Canvas.

The scripts in here will largely rely on the excellent [canvasapi](https://github.com/ucfopen/canvasapi) which hides all the details of your REST calls and lets you focus on the logic of your code. It may or may not be difficult to slot these into your own management of a Canvas instance, given how tailored they are to my particular needs, but my hope is that it can at least be used as a source of known working example code to help people see how certain function calls need to be formatted, how certain things *can* be done, etc.

I will attempt to attach sample configuration files along with documentation on our use case for each script, as well as the kind of actions it's taken to assist in finding code that you can potentially reuse for similar actions.

## Configuration

These scripts expect the URL of your Canvas instance as well as the token to be used with API calls to be set as environment variables.

```
export CANVAS_LMS_URL="https://myinstitution.instructure.com"
export CANVAS_LMS_TOKEN="secret"
```

You will also need to install any required libraries using the pip tool. The included requirements.txt should contain the required libraries for all tools in this repo.

```
pip install -r requirements.txt
```
Other configuration aspects will vary by tool - I hope to rewrite these to be more consistent in the future.
