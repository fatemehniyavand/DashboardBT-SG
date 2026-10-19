# ∿ tick wave — Research in Motion

English Streamlit experience for the complete TickTide research pipeline.

```bash
.venv/bin/python -m pip install -r ticktide_observatory/requirements.txt
.venv/bin/python -m streamlit run ticktide_observatory/app.py --server.port 8510
```

## Motion and navigation

- A fixed SVG behavior tree preserves every branch during replay. Actual event order drives green activation, pulses, retry attempts and rose failure states. The incoming-request envelope is an explicitly labeled visual start marker.
- Filter by recorded Strategy A, Strategy B or Recovery, then select a Run. Play, pause, step, reset and change speed inside each canvas. Use Fit, Zoom or Fullscreen for different viewing sizes. The outer chapter action restarts its scene.
- Moving light packets illustrate flow; they are not physical timing measurements. Other graph chapters use a clearly labeled illustrative graph-reveal order.
- Core racks, edge processors, access radio gateways, request envelopes, Kafka topics and database symbols are inline vectors. Graph coordinates remain stable; no force simulation changes the scene.
- Bar charts include Animate values and Pause. Animation interpolates toward real artifact values; intermediate animation frames are not additional observations.
- Browser reduced-motion preference disables autoplay and CSS motion. Manual stepping remains available. Fonts have local fallbacks.

## Research chapters

Behavior tree → execution replay → executed trees → Prolog service graph → resource demand → infrastructure → MILP placement → routes and independent audit → multi-seed atlas → Kafka architecture and provenance.

**Run live HiGHS optimization** performs a new solve in session memory. Archived placement reuse requires matching all service workloads and normalized dependencies; the representative Run is labeled. Existing artifacts are preserved.

The Kafka scene derives its topic wiring from `ticktide_kafka_automation/automation.py`: `ticktide.sg.ready`, `ticktide.placement.completed`, and the `ticktide.pipeline.errors` branch. It is an architecture preview; connection and delivery remain **not verified**. The dashboard sends no messages and makes no database writes. Launch commands are available inside the chapter.

All resource/delay inputs are synthetic. Costs are reference units. Delay bounds concern per-dependency propagation rather than an end-to-end SLA. Independent audits validate feasibility and objective arithmetic; aggregate CSV values remain archived evidence.

## Six-card live wall (default)

The 3 × 2 wall contains the full behavior tree, trace/service graph, CPU/RAM/bandwidth, placement/routing, deployment decisions/capacity evidence, and Kafka architecture.

Select your recorded path and scenario, then click **Run selected path** once to start. Every subsequent **Run next execution** advances to the next recorded Run within that path filter; the last wraps to the first. Selecting another Run manually or changing the scenario/experiment resets playback; the next click starts that selection.

After launch all six panels animate concurrently and independently. Each restarts its own loop; none waits for another stage. The full-tree loop is 7.2 seconds, service graph 6.4 seconds, resource charts 5.1 seconds, site pulse 2.7 seconds, deployment focus 7.9 seconds and Kafka preview 7.6 seconds at normal speed. A shared Pause/Resume and Speed control affects all clocks. The 36-second wave indicator is a presentation counter rather than a gating scheduler.

Selected compute sites stay **gold** throughout playback; unselected sites stay blue-gray. Hosting labels and tooltips list actual placed services. Moving packets follow used physical hops only. Co-located dependencies are explicitly counted and never assigned fabricated network hops.

CPU, resident RAM and outbound labeled-data bandwidth use vector icons, separate color channels, animated bars and circular reveals. Displayed numerical demands are exact fixed values; animated bar/ring positions illustrate reveal rather than measured utilization. Scenario assumptions appear above the cards, including request rate, ingress pinning, Core overlay and dependency delay limit. All six scenarios are selectable above the wall before Run. Combined is the initial choice; the selected scenario controls demand, placement, routes and effective capacity. The deployment decision studio replaces the former scenario-cost comparison, showing per-service host assignments, F1 pinning, exact CPU/RAM occupancy and block limits. Rotating dots indicate replay; occupancy arcs retain their actual values. Core-only placements remain visible when supported by the archived solution.

Expand any card while the timeline continues. The detailed ten-chapter workspace remains available. Playback never re-solves optimization, rewrites outputs, publishes Kafka messages, or claims live measurement. Tests: `.venv/bin/python ticktide_observatory/test_wall.py`.
