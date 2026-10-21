"""vpce - headless control surface for Visual Paradigm.

Layering (imports only go downward):

    cli / mcp_server      transports: parse input, format output, nothing else
        |
    service               use cases; depends on ports only
        |
    ports                 protocols the adapters must satisfy
        |
    adapters              the only place that touches JVM, APPDATA, files
        |
    core                  pure data: spec, layout, XML model, errors

`core` never imports `adapters`, and nothing outside `adapters` starts a
process or reads the environment.
"""

__version__ = '0.3.0'
