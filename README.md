# Party Parrot

<img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNXl1NGRjNzkxeHc1bnpkNjdybXRpOGRlbWk0c2s1aGgyaDZpNHJzaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l3q2zVr6cu95nF6O4/giphy.gif" />

Party Parrot is a lighting-designer robot companion for DJs.

It listens on your computer's microphone, then coordinates any number of DMX fixtures. It currently supports:
 - Moving lights
 - Moving led bars
 - LED Pars
 - Lasers

Via Entec Pro USB -> DMX


# Installation

1. `brew install portaudio`
2. `brew install python-tk@3.12`
3. `poetry install`

# Run

`./main.sh`

# Testing

To run the test suite:

```bash
# Run all tests
poetry run python -m unittest discover -s parrot

# Run specific test files
poetry run python -m unittest parrot/director/test_director.py
poetry run python -m unittest parrot/fixtures/test_base.py
poetry run python -m unittest parrot/test_main.py
```

The test suite includes unit tests for:
- Fixture base classes and groups
- Director initialization and color scheme management
- Command-line argument parsing

# Web Interface

Party Parrot includes a mobile-friendly web interface that allows you to control the lighting phrases from any device on your local network. When the application starts, it will display a URL in the console that you can use to access the web interface.

The web interface provides buttons to switch between different lighting phrases:
- **Party**: High-energy lighting with beat detection
- **Twinkle**: Gentle, ambient lighting effects
- **Blackout**: Turn off all lighting fixtures

Changes made through the web interface are thread-safe and will be immediately reflected in the lighting system.

You can customize the web server with the following command-line options:
- `--web-port PORT`: Set the web server port (default: 4040)
- `--no-web`: Disable the web server

Example:
```
./main.sh --web-port 8080
```

# List devices

`poetry run python -m DMXEnttecPro.utils`