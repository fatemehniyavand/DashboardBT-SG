# tick wave / Ocean Edition · V2

A separate visual edition of the dashboard based on the user's logo reference: cyan `#2DBBEA`, violet `#BB80F5`, periwinkle `#8488EF`, white and near-black. The supplied reference is reconstructed as a scalable SVG in `assets/tick_wave_logo.svg`; this is a vector reconstruction, not the original attached image file.

## Streamlit deployment

- Repository: `fatemehniyavand/DashboardBT-SG`
- Branch: `main`
- **Main file path: `streamlit_app_v2.py`**

For V1 keep selecting `streamlit_app.py`. Locally:

```bash
python -m streamlit run streamlit_app_v2.py
```

The Ocean Edition shares the existing data model and playback controls. It adds a branded ocean header, layered sea surfaces, flowing wave lines in the panels, cyan node activation, violet selected hosts and a consistent palette in both the wall and detailed chapter scenes. Failure states remain rose and have explicit status labels. Motion respects the existing Pause control and reduced-motion CSS preferences.

The six visual currents are the ripple (behavior tree), current (service graph), resource demand, tide (physical routing), harbor (deployment evidence), and event stream (Kafka/Neo4j preview). These metaphors describe presentation. Wave travel does not establish measured request latency, throughput or deployment activity.

V2 applies its palette to presentation templates **before** artifact JSON is inserted. Scenario definitions, results, audits, run sequencing and recorded data remain unchanged. V1 remains the default for the original launcher.

Validation:

```bash
python bootstrap_data.py   # only needed in a fresh clone
python ticktide_observatory/test_wall.py
python ticktide_observatory/test_ocean.py
```

## Living Ocean / Surf Edition

For the approved high-motion edition select **`streamlit_app_ocean.py`** as the Streamlit main file on branch `main`. This preserves the V1 and initial V2 launchers. It adds a pulsing, flowing logo, buoy-like logo movement, multi-layer rolling sea waves in the header and every card, foam particles and light trails along actual active paths. **Visual sea** offers Calm, Swell and Surf; it affects presentation amplitude only. Panel water follows the shared playback clock and pauses with it; reduced-motion settings freeze decorative water.

```bash
python -m streamlit run streamlit_app_ocean.py
```
