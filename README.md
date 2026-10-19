# ∿ tick wave — Behavior Tree → Service Graph Dashboard

An English Streamlit dashboard for the TickTide research workflow, with six concurrent animated panels and a detailed ten-chapter explorer.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

The first launch verifies and extracts `research_data.zip`. It contains the existing synthetic research outputs for seeds **42, 123, 2026**: 1,000 recorded executions per seed and six archived placement scenarios. No database connection is needed.

## Ocean Edition · V2

The second visual edition uses the supplied cyan/violet logo reference, a scalable vector logo, sea-wave motion and a separate launch file. In Streamlit Community Cloud choose **`streamlit_app_v2.py`** on the **`main`** branch. The original **`streamlit_app.py`** keeps the V1 appearance. See [Ocean Edition documentation](ticktide_observatory/README_OCEAN.md).

```bash
python -m streamlit run streamlit_app_v2.py
```

## Living Ocean / Surf Edition · Latest

For the high-motion version, choose **`streamlit_app_ocean.py`** as the Streamlit main file on branch **`main`**. This edition includes the animated cyan/violet logo, rolling layered ocean waves, foam and request light trails. All six panels loop independently; Visual sea controls Calm / Swell / Surf. The previous launch files remain available.

```bash
python -m streamlit run streamlit_app_ocean.py
```

## Explore

1. Choose a placement scenario above the dashboard.
2. Select a recorded strategy path and Run in the sidebar.
3. Click **Run selected path** to start all six independent animation loops.
4. Click **Run next execution** to advance within that path filter.
5. Expand a panel to inspect detail, pause playback or change speed.

The panels show the behavior tree, Prolog-derived service graph, CPU/RAM/data bandwidth, actual Edge/Core placement and routing, per-service deployment and effective capacity, and Kafka/Neo4j architecture preview. Gold infrastructure nodes are actual selected hosts. The deployment studio displays real scenario capacity and occupancy; animation timing is illustrative.

The detailed chapter view also supports a new HiGHS MILP solve in session memory and independent feasibility recomputation. The Kafka scene is a preview: it does not connect to a broker, send messages or write Neo4j. Operational Kafka commands shown in the interface refer to the original research bundle and are not included in this dashboard distribution.

## Validate

```bash
python bootstrap_data.py
python ticktide_observatory/test_wall.py
```

Four regression tests cover Run advancement, filtered-path wraparound, six-scenario selection, matching placement evidence and effective Core capacity.

## Scientific scope

Inputs are synthetic. Costs are reference units, not currency. Delay bounds constrain per-dependency propagation, not end-to-end latency. Core-only placement is a valid recorded result in scenarios that do not require Edge placement. Audit checks establish feasibility and objective arithmetic for the implemented model. Read [the methodology](README_RESEARCH_METHOD.md) and [dashboard documentation](ticktide_observatory/README.md).

The source is supplied for the user's TickTide research project; upstream source/license attribution is retained in the files. No new license is asserted for inherited research code.
