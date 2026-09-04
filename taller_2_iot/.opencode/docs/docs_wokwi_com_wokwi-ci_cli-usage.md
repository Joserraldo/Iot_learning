# Wokwi CLI Usage | Wokwi Docs

> Source: https://docs.wokwi.com/wokwi-ci/cli-usage
> Cached: 2026-09-03T19:00:36.900Z

---

- [](/)
- Wokwi CI
- CLI Usage

On this page# Wokwi CLI Usage

Create an API token on the [Wokwi CI Dashboard](https://wokwi.com/dashboard/ci). Set the `WOKWI_CLI_TOKEN` environment variable to the token value.

If you haven&#x27;t set up your project for Wokwi yet, you can use the `init` command to configure your project for Wokwi. Run the following command in your project&#x27;s root directory:

```
wokwi-cli init

```

This command will ask you a few questions and will automatically generate [wokwi.toml](/vscode/project-config) and [diagram.json](/diagram-format) files for your project.

To run the simulation, use the following command:

```
wokwi-cli <your-project-directory>

```

The CLI will start the simulation and display the serial output. It will automatically exit after 30 seconds.

tipA valid Wokwi CLI token starts with `wok_` and is exactly 44 characters long (including the `wok_` prefix). If you are
experiencing authorization issues, double check that your token is active, correctly formatted and doesn&#x27;t contain any
spaces or fancy characters.
## CLI Options[​](#cli-options)

You can use the following options to customize the CLI behavior:

### Configuration[​](#configuration)

- `--elf <path>` - ELF file to simulate (default: read from wokwi.toml)

- `--diagram-file <path>` - Path to the diagram.json file, relative to project root (default: diagram.json)

- `--interactive` - Redirect stdin to the simulated serial port

- `--serial-log-file <path>` - Save the serial monitor output to the given file

- `--timeout <number>` - Timeout in simulation milliseconds (default: 30000)

- `--timeout-exit-code <number>` - Process exit code when timeout is reached (default: 42)

### Automation[​](#automation)

- `--expect-text <string>` - Expect the given text in the output

- `--fail-text <string>` - Fail if the given text is found in the output

- `--scenario <path>` - Path to an [automation scenario](/wokwi-ci/automation-scenarios) file, relative to project root

- `--screenshot-part <string>` - Take a screenshot of the given part id (from diagram.json)

- `--screenshot-time <number>` - Time in simulation milliseconds to take the screenshot

- `--screenshot-file <string>` - File name to save the screenshot to (default: screenshot.png)

- `--vcd-file <path>` - Export [Logic Analyzer](/parts/wokwi-logic-analyzer) data to a VCD file

### General[​](#general)

- `--help`, `-h` - Prints help information and exit

- `--quiet`, `-q` - Quiet: do not print version or status messages

## Linting Diagrams[​](#linting-diagrams)

The `lint` command validates your [diagram.json](/diagram-format) file for errors and warnings before running a simulation:

```
wokwi-cli lint

```

The linter checks for common issues such as unknown part types, invalid pin connections, and missing components. By default, it fetches the latest board definitions from the Wokwi registry to ensure accurate validation.

[Edit this page](https://github.com/wokwi/wokwi-docs/edit/main/docs/wokwi-ci/cli-usage.md)