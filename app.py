import os
import zipfile
import glob
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from flask import Flask, render_template, request

# Initialize Flask app with auto-reload for templates
app = Flask(__name__, template_folder="templates")
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Define directories
ZIP_FOLDER = os.path.abspath("csv_files")  # Ensure absolute paths
EXTRACT_FOLDER = os.path.abspath("extracted_files")

# Ensure extraction folder exists
os.makedirs(EXTRACT_FOLDER, exist_ok=True)

# Step 1: **Extract ZIP Files & Ensure All CSVs Are Read Correctly**
zip_files = glob.glob(os.path.join(ZIP_FOLDER, "*.zip"))
if not zip_files:
    print("❌ No ZIP files found in 'csv_files/'. Please check the folder.")
else:
    print(f"🗂 Found {len(zip_files)} ZIP files. Extracting all CSVs...")
    for zip_file in zip_files:
        try:
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith(".csv"):  # Extract only CSV files
                        extracted_path = os.path.join(EXTRACT_FOLDER, os.path.basename(file))
                        with zip_ref.open(file) as source, open(extracted_path, "wb") as target:
                            target.write(source.read())
                        print(f"✅ Extracted: {file} → {extracted_path}")
        except Exception as e:
            print(f"❌ Error extracting {zip_file}: {e}")

# Step 2: **Dynamically Select All Extracted CSVs**
csv_files = sorted(glob.glob(os.path.join(EXTRACT_FOLDER, "*.csv")), key=os.path.getmtime, reverse=True)

if not csv_files:
    print("❌ ERROR: No extracted CSV files found in 'extracted_files/'. Ensure ZIP extraction is working.")
    exit(1)

print(f"📊 Flask will use these extracted files: {csv_files}")

# Step 3: **Load & Merge All CSVs Like Jupyter Notebook**
all_data_frames = []
for file in csv_files:
    try:
        df = pd.read_csv(file, encoding="utf-8-sig")  # Ensure correct encoding
        if df.empty:
            print(f"⚠️ Warning: {file} is empty and was skipped.")
        else:
            print(f"✅ Loaded {file} ({df.shape[0]} rows, {df.shape[1]} columns).")
            all_data_frames.append(df)
    except Exception as e:
        print(f"❌ Error loading {file}: {e}")

# Merge into a single DataFrame
if all_data_frames:
    df = pd.concat(all_data_frames, ignore_index=True)
    print(f"✅ Merged {len(all_data_frames)} files into `df` ({df.shape[0]} rows).")
else:
    print("❌ No valid data loaded. Check extracted CSV files.")
    exit(1)

# Step 5: **Clean and Process Data**
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=True)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df.dropna(subset=["date"], inplace=True)

print("✅ Column names standardized and date column processed.")

# ✅ Set Default Values for Flask UI
DEFAULT_ATHLETE = df["name"].unique()[0]
DEFAULT_VAR1 = "time_to_takeoff"
DEFAULT_VAR2 = "mrsi"

def create_app():
    """ Factory function to create Flask app """
    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index():
        print("🔄 Received request for dashboard")

        athlete = request.form.get("athlete", DEFAULT_ATHLETE)
        var1 = request.form.get("var1", DEFAULT_VAR1)
        var2 = request.form.get("var2", DEFAULT_VAR2)
        start_date = request.form.get("start_date", df["date"].min())
        end_date = request.form.get("end_date", df["date"].max())

        plot_html = create_plot(athlete, var1, var2, start_date, end_date)

        return render_template("index.html", plot_html=plot_html, athletes=df["name"].unique(), variables=df.columns.tolist())

    return app

def create_plot(athlete, var1, var2, start_date, end_date):
    """ Function to generate Plotly graph """
    print(f"📊 Generating plot for {athlete} ({var1} vs {var2})")

    filtered_df = df[
        (df["name"] == athlete) & 
        (df["date"] >= pd.to_datetime(start_date)) & 
        (df["date"] <= pd.to_datetime(end_date))
    ]

    if filtered_df.empty:
        print("⚠️ WARNING: No data available for the selected filters.")
        return "<h3>No data available for the selected athlete and date range.</h3>"

    fig = go.Figure()

    # Add trace for Variable 1 (Left y-axis) - RED
    fig.add_trace(go.Scatter(
        x=filtered_df["date"],
        y=filtered_df[var1],
        mode="lines+markers",
        name=var1,
        line=dict(color='red', shape='spline', width=3),
        fill='tonexty',
        fillcolor='rgba(255, 0, 0, 0.3)'  # Red shading
    ))

    # Add trace for Variable 2 (Right y-axis) - YELLOW
    fig.add_trace(go.Scatter(
        x=filtered_df["date"],
        y=filtered_df[var2],
        mode="lines+markers",
        name=var2,
        line=dict(color='yellow', shape='spline', width=3),
        fill='tonexty',
        fillcolor='rgba(255, 255, 0, 0.3)',  # Yellow shading
        yaxis="y2"
    ))

    # Set layout with black background and red/yellow styling
    fig.update_layout(
        title=f"Performance Over Time - {athlete}",
        xaxis=dict(title="Date", tickformat="%m-%d", gridcolor="gray", color="white"),
        yaxis=dict(title=f"{var1}", gridcolor="gray"),
        yaxis2=dict(title=f"{var2}", overlaying="y", side="right", gridcolor="gray"),
        paper_bgcolor="black",  
        plot_bgcolor="black",  
        template="plotly_dark",
        showlegend=True
    )

    return pio.to_html(fig, full_html=False)

from flask import Flask, render_template

app = Flask(__name__, template_folder="templates")

@app.route("/")
def home():
    return "Flask is working!"  # TEMPORARY TEST

# Print all Flask routes to debug
with app.test_request_context():
    print(app.url_map)

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)