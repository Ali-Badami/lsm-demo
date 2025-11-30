import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# --- CONFIGURATION & STYLING ---
st.set_page_config(page_title="Deferred Updates: LSM Research Demo", page_icon="⚡", layout="wide")

st.title("⚡ Optimizing LSM Trees with Deferred Updates")
st.markdown("""
**Research Implementation of:** *Optimizing LSM Tree Operations with Deferred Updates: A Comparative Study* This interactive tool simulates the **theoretical speedup** and **read-latency trade-offs** proposed in the paper.
""")

# --- SIDEBAR: GLOBAL PARAMETERS ---
with st.sidebar:
    st.header("⚙️ Experimental Setup")
    
    # Parameters from Paper Section IV (Mathematical Foundations)
    st.subheader("LSM Tree Parameters")
    N_tuples = st.number_input("Total Tuples (N)", value=10_000_000, step=1_000_000, format="%d")
    m_memtable = st.number_input("Memtable Size (m)", value=100_000, step=10_000, format="%d")
    K_indexes = st.slider("Number of Indexes (K)", min_value=1, max_value=10, value=5, help="Primary + Secondary Indexes")
    
    # Constants for Big-O approximation (approximate IO costs)
    st.subheader("Hardware Constants")
    disk_seek_cost = st.slider("Disk Seek Cost (relative to RAM)", 1, 100, 50, help="SSD/HDD latency factor")

# --- TABS FOR DIFFERENT SECTIONS ---
tab1, tab2, tab3 = st.tabs(["🚀 Write Speedup (Theory)", "📉 Read Latency Trade-off", "🧠 How it Works"])

# --- TAB 1: THEORETICAL SPEEDUP (Section IV) ---
with tab1:
    st.subheader("Theoretical Complexity Analysis (Section IV)")
    st.markdown("Comparing the cost of **Regular Updates** vs. **Deferred Updates (Blind Writes)**.")

    # --- MATH IMPLEMENTATION ---
    # Based on formulas from [cite: 340] and [cite: 349]
    # Log bases are simplified for simulation (log_b m treated as memory access unit)
    
    # 1. Cost of Regular Replace: Hidden Read (Disk + RAM) + Update all indexes
    # Formula: O(log_b m) + O(log_r(N-m)) + O(log_b m) * (2K - 1)
    cost_regular = (1) + (np.log10(max(1, N_tuples - m_memtable)) * disk_seek_cost) + (1 * (2 * K_indexes - 1))
    
    # 2. Cost of Deferred Replace: Blind Write to RAM only
    # Formula: O(log_b m) * K
    cost_deferred = (1 * K_indexes)

    speedup = cost_regular / cost_deferred

    # --- VISUALIZATION ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Regular Cost (Ops)", f"{cost_regular:.1f}", help="High due to hidden reads on disk")
    col2.metric("Deferred Cost (Ops)", f"{cost_deferred:.1f}", help="Low, only memory inserts")
    col3.metric("Theoretical Speedup", f"{speedup:.2f}x", delta="Positive", delta_color="normal")

    # Simulation: Speedup vs Number of Indexes (K)
    st.markdown("#### Impact of Secondary Indexes (K)")
    k_range = list(range(1, 21))
    results = []
    for k in k_range:
        c_reg = (1) + (np.log10(max(1, N_tuples - m_memtable)) * disk_seek_cost) + (1 * (2 * k - 1))
        c_def = (1 * k)
        results.append({'K': k, 'Speedup': c_reg / c_def})
    
    df_chart = pd.DataFrame(results)
    
    fig = px.line(df_chart, x='K', y='Speedup', markers=True, 
                  title="Speedup Factor vs. Number of Indexes",
                  labels={'K': 'Number of Secondary Indexes', 'Speedup': 'Speedup Factor (X times)'})
    fig.add_annotation(x=5, y=df_chart[df_chart['K']==5]['Speedup'].values[0], text="Your Paper's Setup", showarrow=True)
    st.plotly_chart(fig, use_container_width=True)
    
    st.info(f"**Insight:** As shown in the graph, the speedup decreases as K increases, but remains significant. For K={K_indexes}, we eliminate the costly 'Hidden Read' ($O(\log_r (N-m))$), converting random disk reads into blind memory writes[cite: 100].")

# --- TAB 2: READ LATENCY TRADE-OFF (Section V-D) ---
with tab2:
    st.subheader("The 'Dirty Tuple' Penalty (LinkBench Results)")
    st.markdown("""
    While deferred updates boost writes, they introduce **"Dirty Tuples"**—ghost records in secondary indexes that must be checked against the primary index during reads[cite: 251].
    """)

    # --- SIMULATION ---
    write_ratio = st.slider("Workload Write %", 0, 100, 50)
    
    # Model: As writes increase, "Dirty Tuples" accumulate, slowing down reads.
    # Base read time = 1ms. Dirty tuple check cost = 0.5ms per dirty tuple.
    base_read_time = 1.0
    dirty_tuple_prob = write_ratio / 100.0  # Higher writes = more dirty tuples
    
    # Simulating read latency
    latency_regular = base_read_time # Regular LSM has clean indexes (updates happen immediately)
    latency_deferred = base_read_time + (dirty_tuple_prob * 2.5) # Penalty for checking primary index
    
    col_l1, col_l2 = st.columns(2)
    col_l1.metric("Regular Read Latency", f"{latency_regular} ms")
    col_l2.metric("Deferred Read Latency", f"{latency_deferred:.2f} ms", delta=f"-{(latency_deferred-latency_regular):.2f} ms", delta_color="inverse")

    # Chart: Throughput vs Latency
    st.markdown("#### Throughput vs. Latency Trade-off")
    
    # Generate data for trade-off curve
    ratios = np.linspace(0, 100, 20)
    tradeoff_data = []
    
    for r in ratios:
        # Write heavy = High speedup, High latency penalty
        # Read heavy = Low speedup, Low latency penalty
        s_factor = speedup * (r/100) # Simple weight for demo
        l_penalty = (r/100) * 3.0
        tradeoff_data.append({'Write %': r, 'Metric': 'Write Speedup', 'Value': s_factor})
        tradeoff_data.append({'Write %': r, 'Metric': 'Read Latency Penalty', 'Value': l_penalty})

    df_tradeoff = pd.DataFrame(tradeoff_data)
    fig2 = px.line(df_tradeoff, x='Write %', y='Value', color='Metric', 
                   title="System Performance based on Workload Type")
    st.plotly_chart(fig2, use_container_width=True)
    
    st.warning("**Conclusion:** Your algorithm is optimal for **Write-Intensive** workloads (Microbench) but incurs a read penalty in Read-Intensive scenarios (LinkBench).")

# --- TAB 3: EDUCATIONAL VISUALIZER ---
with tab3:
    st.subheader("How Deferred Updates Work")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("### 🔴 Traditional Approach")
        st.error("""
        1. **User:** `REPLACE {id:1, val:99}`
        2. **System:** 🛑 **STOP!** I need to check consistency.
        3. **Read:** Go to Disk ➡️ Find old tuple `{id:1, val:50}`.         4. **Delete:** Remove `{val:50}` from Secondary Index.
        5. **Write:** Insert `{val:99}`.
        """)
    
    with col_b:
        st.markdown("### 🟢 Your Deferred Algorithm")
        st.success("""
        1. **User:** `REPLACE {id:1, val:99}`
        2. **System:** ✅ **OK!** Writing to Memory immediately. (Blind Write) [cite: 93]
        3. **Note:** Old tuple `{val:50}` is now a **"Dirty Tuple"**.
        4. **Later:** During **Compaction**, we see both versions and clean up.
        """)
    
    st.markdown("---")
    st.markdown("### Glossary of Terms [cite: 35]")
    with st.expander("📚 View Definitions"):
        st.markdown("""
        * **Blind Writes:** Write operations that do not verify data consistency by reading prior data[cite: 38].
        * **Hidden Reads:** Reads that accompany write operations to verify consistency or delete old data[cite: 39].
        * **Dirty Tuples:** Secondary index entries that persist even after the primary index entry is deleted[cite: 37].
        """)

# --- FOOTER ---
st.markdown("---")
st.caption("Simulation based on *Badami, S. (2024). Optimizing LSM Tree Operations with Deferred Updates*.")
