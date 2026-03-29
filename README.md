# Bitsy Poker Simulator

A custom Texas Hold'em Poker engine and bot simulation framework written in Python.

## Overview

This project provides a complete environment to develop, train, and test various poker bots, including Reinforcement Learning implementations like Counterfactual Regret Minimization (CFR) and Monte Carlo approaches. It features a generic `Player` architecture that makes it easy to integrate custom strategies.

## Features

- **Custom Player Architecture**: Easily extend the `Player` class to build your own custom bots. 
- **Strategy Bots**:
  - `bot_aggressive.py`: Uses hand strength estimation and pot odds calculations to perform aggressive betting and bluffing.
  - `bot_mccfr.py`: A bot utilizing Monte Carlo Counterfactual Regret Minimization logic to inform actions.
  - `bot_cfr.py`: A player bot configured to load pretrained CFR strategies from static `.pkl` files.
- **Hand Evaluator**: Fast internal logic implemented in `hand_evaluator.py` to rank complete hands and resolve showdowns correctly.
- **Simulation Harness**: Start the game via `main.py`, run multiple hands consecutively, tweak parameters like big blinds and stack sizes, and compare strategies against offline opponents.

## Setup

Make sure you have installed the recommended dependency, which is used by the MCCFR and Aggressive bots for hand equity estimation:

```bash
pip install pypokerengine
```

## Running a Game

Run a sample game via the command line interface:

```bash
python main.py
```
