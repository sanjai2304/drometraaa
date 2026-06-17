import pandas as pd
import numpy as np
import os
import joblib
import time
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import StratifiedKFold, RandomizedSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, roc_curve
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, VotingClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier

# Create output directories
os.makedirs("models", exist_ok=True)
os.makedirs("plots", exist_ok=True)

# ---------------------------------------------------------
# 1. Custom Safe Label Encoder for Robust Production Use
# ---------------------------------------------------------
class SafeLabelEncoder:
    def __init__(self, default_val=-1):
        self.classes_ = None
        self.mapping_ = {}
        self.inverse_mapping_ = {}
        self.default_val = default_val
    
    def fit(self, s):
        unique_vals = sorted(pd.Series(s).dropna().astype(str).unique())
        self.classes_ = unique_vals
        self.mapping_ = {val: idx for idx, val in enumerate(unique_vals)}
        self.inverse_mapping_ = {idx: val for idx, val in enumerate(unique_vals)}
        return self
    
    def transform(self, s):
        return pd.Series(s).astype(str).map(self.mapping_).fillna(self.default_val).astype(int)
    
    def fit_transform(self, s):
        self.fit(s)
        return self.transform(s)
        
    def inverse_transform(self, s):
        return pd.Series(s).map(self.inverse_mapping_).fillna("Unknown")

# ---------------------------------------------------------
# 2. Data Loading & Cleaning
# ---------------------------------------------------------
print("Loading dataset...")
filepath = r"dataset/Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv"
if not os.path.exists(filepath):
    # Try alternate path just in case
    filepath = r"d:\croud project\dataset\Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv"

df = pd.read_csv(filepath)

# Parse datetimes
df['start_datetime'] = pd.to_datetime(df['start_datetime'], errors='coerce')
df['closed_datetime'] = pd.to_datetime(df['closed_datetime'], errors='coerce')

# Drop rows with missing crucial location or timestamp
df = df.dropna(subset=['start_datetime', 'latitude', 'longitude']).copy()

# Sort chronologically to prevent temporal data leakage
df = df.sort_values('start_datetime').reset_index(drop=True)

print(f"Data shape after cleaning null datetimes: {df.shape}")

# ---------------------------------------------------------
# 3. Feature Engineering
# ---------------------------------------------------------
print("Engineering features...")

# Time features
df['hour'] = df['start_datetime'].dt.hour
df['weekday'] = df['start_datetime'].dt.weekday
df['month'] = df['start_datetime'].dt.month
df['is_weekend'] = (df['weekday'] >= 5).astype(int)
df['rush_hour'] = df['hour'].apply(lambda x: 1 if (8 <= x <= 11) or (17 <= x <= 20) else 0)

# Weather impact score (mapped from event cause)
# Heavy rain causes water logging and tree falls which impact traffic heavily
def get_weather_impact(cause):
    cause = str(cause).lower()
    if 'water_logging' in cause:
        return 2.5
    elif 'tree_fall' in cause:
        return 2.0
    elif 'fog' in cause or 'visibility' in cause:
        return 1.5
    elif 'rain' in cause:
        return 1.5
    return 0.0

df['weather_impact_score'] = df['event_cause'].apply(get_weather_impact)

# Traffic pressure score: Rolling count of events starting in the same corridor in the past 3 hours
# To prevent data leakage, we compute it chronologically
corridor_times = df[['start_datetime', 'corridor']].copy()
pressure_scores = []
for idx, row in df.iterrows():
    curr_time = row['start_datetime']
    curr_corridor = row['corridor']
    # Filter for previous 3 hours in same corridor
    past_3h = curr_time - pd.Timedelta(hours=3)
    recent_cnt = corridor_times[
        (corridor_times['corridor'] == curr_corridor) & 
        (corridor_times['start_datetime'] >= past_3h) & 
        (corridor_times['start_datetime'] < curr_time)
    ].shape[0]
    pressure_scores.append(recent_cnt)

df['traffic_pressure_score'] = pressure_scores

# Event density score: Running cumulative count of historical events in the same police station
ps_counts = {}
density_scores = []
for idx, row in df.iterrows():
    curr_ps = row['police_station']
    if pd.isna(curr_ps):
        curr_ps = 'Unknown'
    cnt = ps_counts.get(curr_ps, 0)
    density_scores.append(cnt)
    ps_counts[curr_ps] = cnt + 1

df['event_density_score'] = density_scores

# Event Impact Score (Formula-based Footprint indicator)
# Normalized from 1 to 10
# Formula: closure_weight + priority_weight + cause_weight + veh_weight
def get_cause_weight(cause):
    c = str(cause).lower()
    if 'accident' in c: return 2.5
    if 'water_logging' in c: return 2.5
    if 'tree_fall' in c: return 2.0
    if 'construction' in c: return 2.0
    if 'breakdown' in c: return 1.5
    if 'road_conditions' in c or 'pot_holes' in c: return 1.5
    if 'vip_movement' in c or 'protest' in c or 'procession' in c: return 2.0
    return 1.0

def get_veh_weight(veh):
    v = str(veh).lower()
    if v in ['heavy_vehicle', 'bmtc_bus', 'ksrtc_bus', 'private_bus', 'truck']:
        return 2.0
    if v == 'lcv':
        return 1.2
    if v in ['private_car', 'taxi', 'auto']:
        return 0.8
    return 1.0

df['event_cause_weight'] = df['event_cause'].apply(get_cause_weight)
df['veh_type_weight'] = df['veh_type'].apply(get_veh_weight)
df['requires_road_closure_val'] = df['requires_road_closure'].apply(lambda x: 3.0 if x else 0.0)
df['priority_val'] = df['priority'].apply(lambda x: 2.0 if str(x).lower() == 'high' else 0.0)

raw_impact = df['requires_road_closure_val'] + df['priority_val'] + df['event_cause_weight'] + df['veh_type_weight']
# Normalize between 1 and 10
min_imp, max_imp = raw_impact.min(), raw_impact.max()
if max_imp - min_imp > 0:
    df['event_impact_score'] = 1 + 9 * (raw_impact - min_imp) / (max_imp - min_imp)
else:
    df['event_impact_score'] = 5.0

# ---------------------------------------------------------
# 4. Innovation Feature: Congestion Spread Prediction Target
# ---------------------------------------------------------
print("Computing congestion spread target (is_spread)...")
lat = df['latitude'].values
lon = df['longitude'].values
times = df['start_datetime'].values

n = len(lat)
is_spread = np.zeros(n, dtype=int)
lat_rad = np.radians(lat)
lon_rad = np.radians(lon)

for i in range(n):
    t_i = times[i]
    limit_time = t_i + np.timedelta64(2, 'h')  # 2 hours window
    for j in range(i+1, n):
        if times[j] > limit_time:
            break
        # Distance calculation
        dlat = lat_rad[j] - lat_rad[i]
        dlon = lon_rad[j] - lon_rad[i]
        a = np.sin(dlat/2)**2 + np.cos(lat_rad[i]) * np.cos(lat_rad[j]) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        dist = 6371.0 * c  # in km
        
        if dist <= 1.5:  # 1.5 km radius
            is_spread[i] = 1
            break

df['is_spread'] = is_spread
print(f"Spread class ratio: {df['is_spread'].mean():.4f}")

# Target Variable Encoding for main model (priority)
# priority: "High" -> 1, "Low" -> 0. Drop rows with null priority.
df = df.dropna(subset=['priority']).copy()
df['priority_encoded'] = df['priority'].apply(lambda x: 1 if str(x).lower() == 'high' else 0)
print(f"Priority class ratio (High severity): {df['priority_encoded'].mean():.4f}")

# Clean categorical fields and replace NaN with 'Unknown'
categorical_cols = ['event_type', 'event_cause', 'veh_type', 'corridor', 'police_station', 'zone', 'gba_identifier', 'junction']
for col in categorical_cols:
    df[col] = df[col].fillna('Unknown').astype(str)

# Save Label Encoders
encoders = {}
for col in categorical_cols:
    le = SafeLabelEncoder()
    df[col + '_encoded'] = le.fit_transform(df[col])
    encoders[col] = le

joblib.dump(encoders, "models/label_encoders.joblib")
print("Saved label encoders.")

# Save dataset with engineered features for dashboard
df.to_parquet("models/engineered_dataset.parquet")
print("Saved engineered dataset.")

# Define model features
features = [
    'latitude', 'longitude', 'requires_road_closure', 
    'event_type_encoded', 'event_cause_encoded', 'veh_type_encoded', 
    'corridor_encoded', 'police_station_encoded', 'zone_encoded', 
    'gba_identifier_encoded', 'junction_encoded',
    'hour', 'weekday', 'month', 'is_weekend', 'rush_hour',
    'weather_impact_score', 'traffic_pressure_score', 'event_density_score'
]

# Ensure requires_road_closure is integer/bool for model
df['requires_road_closure'] = df['requires_road_closure'].astype(int)

# ---------------------------------------------------------
# 5. Temporal Train/Test Split (80% Train, 20% Test)
# ---------------------------------------------------------
split_idx = int(len(df) * 0.8)
train_df = df.iloc[:split_idx].copy()
test_df = df.iloc[split_idx:].copy()

X_train, y_train = train_df[features], train_df['priority_encoded']
X_test, y_test = test_df[features], test_df['priority_encoded']

print(f"Training set: {X_train.shape}, Test set: {X_test.shape}")

# ---------------------------------------------------------
# 6. Model Training & Comparison (5-Fold CV)
# ---------------------------------------------------------
models = {
    'RandomForest': RandomForestClassifier(random_state=42),
    'ExtraTrees': ExtraTreesClassifier(random_state=42),
    'XGBoost': XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42),
    'LightGBM': LGBMClassifier(random_state=42),
    'CatBoost': CatBoostClassifier(verbose=0, random_state=42)
}

results = {}
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

for name, model in models.items():
    print(f"Training {name} with 5-fold CV...")
    oof_preds = np.zeros(len(X_train))
    oof_probs = np.zeros(len(X_train))
    
    cv_start = time.time()
    for fold, (train_idx, val_idx) in enumerate(cv.split(X_train, y_train)):
        X_tr, y_tr = X_train.iloc[train_idx], y_train.iloc[train_idx]
        X_val, y_val = X_train.iloc[val_idx], y_train.iloc[val_idx]
        
        # Fit model
        model.fit(X_tr, y_tr)
        
        oof_preds[val_idx] = model.predict(X_val)
        oof_probs[val_idx] = model.predict_proba(X_val)[:, 1]
    
    cv_time = time.time() - cv_start
    
    # Calculate metrics
    acc = accuracy_score(y_train, oof_preds)
    prec = precision_score(y_train, oof_preds)
    rec = recall_score(y_train, oof_preds)
    f1 = f1_score(y_train, oof_preds)
    auc = roc_auc_score(y_train, oof_probs)
    
    results[name] = {
        'accuracy': acc,
        'precision': prec,
        'recall': rec,
        'f1': f1,
        'auc': auc,
        'cv_time': cv_time
    }
    print(f"  {name} CV Metrics: Accuracy={acc:.4f}, F1={f1:.4f}, AUC={auc:.4f} (Time: {cv_time:.2f}s)")

# Display CV Results Table
results_df = pd.DataFrame(results).T
print("\n=== MODEL COMPARISON TABLE ===")
print(results_df.to_string())

# ---------------------------------------------------------
# 7. Hyperparameter Tuning of Best Model (Automatic Selection)
# ---------------------------------------------------------
best_model_name = results_df['f1'].idxmax()
print(f"\nBest model based on CV F1-score: {best_model_name}")

print("Performing Hyperparameter Tuning...")
tuned_model = None

if best_model_name == 'LightGBM':
    param_grid = {
        'num_leaves': [15, 31, 63],
        'max_depth': [-1, 6, 10],
        'learning_rate': [0.01, 0.05, 0.1],
        'n_estimators': [100, 200, 300]
    }
    search = RandomizedSearchCV(LGBMClassifier(random_state=42), param_distributions=param_grid, 
                               n_iter=5, cv=cv, scoring='f1', n_jobs=-1, random_state=42)
    search.fit(X_train, y_train)
    tuned_model = search.best_estimator_
    print("Tuned LightGBM parameters:", search.best_params_)

elif best_model_name == 'XGBoost':
    param_grid = {
        'max_depth': [3, 6, 9],
        'learning_rate': [0.01, 0.05, 0.1],
        'n_estimators': [100, 200, 300],
        'subsample': [0.8, 1.0]
    }
    search = RandomizedSearchCV(XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42), 
                               param_distributions=param_grid, n_iter=5, cv=cv, scoring='f1', n_jobs=-1, random_state=42)
    search.fit(X_train, y_train)
    tuned_model = search.best_estimator_
    print("Tuned XGBoost parameters:", search.best_params_)

elif best_model_name == 'CatBoost':
    param_grid = {
        'depth': [4, 6, 8],
        'learning_rate': [0.01, 0.05, 0.1],
        'iterations': [100, 200, 300]
    }
    search = RandomizedSearchCV(CatBoostClassifier(verbose=0, random_state=42), param_distributions=param_grid, 
                               n_iter=5, cv=cv, scoring='f1', n_jobs=-1, random_state=42)
    search.fit(X_train, y_train)
    tuned_model = search.best_estimator_
    print("Tuned CatBoost parameters:", search.best_params_)

else: # RandomForest or ExtraTrees
    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [10, 20, None],
        'min_samples_split': [2, 5, 10]
    }
    base_model = RandomForestClassifier(random_state=42) if best_model_name == 'RandomForest' else ExtraTreesClassifier(random_state=42)
    search = RandomizedSearchCV(base_model, param_distributions=param_grid, 
                               n_iter=5, cv=cv, scoring='f1', n_jobs=-1, random_state=42)
    search.fit(X_train, y_train)
    tuned_model = search.best_estimator_
    print(f"Tuned {best_model_name} parameters:", search.best_params_)

# ---------------------------------------------------------
# 8. Ensemble Model Building (Voting Classifier)
# ---------------------------------------------------------
print("\nBuilding Voting Classifier Ensemble of Top Models...")
# Select top 3 models
top_models_names = results_df.sort_values(by='f1', ascending=False).index[:3].tolist()
estimators = []
for m_name in top_models_names:
    if m_name == 'LightGBM':
        estimators.append(('lgb', LGBMClassifier(random_state=42)))
    elif m_name == 'XGBoost':
        estimators.append(('xgb', XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)))
    elif m_name == 'CatBoost':
        estimators.append(('cat', CatBoostClassifier(verbose=0, random_state=42)))
    elif m_name == 'RandomForest':
        estimators.append(('rf', RandomForestClassifier(random_state=42)))
    elif m_name == 'ExtraTrees':
        estimators.append(('et', ExtraTreesClassifier(random_state=42)))

ensemble = VotingClassifier(estimators=estimators, voting='soft')
ensemble.fit(X_train, y_train)

# Compare Tuned Best Model vs Ensemble on held-out test set
print("\n=== EVALUATING ON HELDOUT TEST SET (TEMPORAL VALIDATION) ===")
# Fit best tuned model on training data
tuned_model.fit(X_train, y_train)

for name, clf in [('Tuned Best Model (' + best_model_name + ')', tuned_model), ('Voting Ensemble', ensemble)]:
    preds = clf.predict(X_test)
    probs = clf.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds)
    rec = recall_score(y_test, preds)
    f1 = f1_score(y_test, preds)
    auc = roc_auc_score(y_test, probs)
    
    print(f"{name} Test Metrics:")
    print(f"  Accuracy:  {acc:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall:    {rec:.4f}")
    print(f"  F1-Score:  {f1:.4f}")
    print(f"  ROC-AUC:   {auc:.4f}\n")

# Save the absolute best model (tuned model or ensemble) on test F1-score
ens_preds = ensemble.predict(X_test)
ens_f1 = f1_score(y_test, ens_preds)
tuned_preds = tuned_model.predict(X_test)
tuned_f1 = f1_score(y_test, tuned_preds)

if ens_f1 > tuned_f1:
    best_overall_model = ensemble
    best_overall_name = "Voting Ensemble"
else:
    best_overall_model = tuned_model
    best_overall_name = "Tuned " + best_model_name

print(f"Selected {best_overall_name} as final model.")
joblib.dump(best_overall_model, "models/final_severity_model.joblib")
print("Saved final severity model to models/final_severity_model.joblib")

# ---------------------------------------------------------
# 9. Train Congestion Spread Prediction Model
# ---------------------------------------------------------
print("\nTraining Congestion Spread Prediction Model (is_spread)...")
y_train_spread = train_df['is_spread']
y_test_spread = test_df['is_spread']

spread_model = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
spread_model.fit(X_train, y_train_spread)

spread_preds = spread_model.predict(X_test)
spread_probs = spread_model.predict_proba(X_test)[:, 1]
print(f"Spread Model Test Metrics:")
print(f"  Accuracy: {accuracy_score(y_test_spread, spread_preds):.4f}")
print(f"  F1-Score: {f1_score(y_test_spread, spread_preds):.4f}")
print(f"  ROC-AUC:  {roc_auc_score(y_test_spread, spread_probs):.4f}")

joblib.dump(spread_model, "models/spread_prediction_model.joblib")
print("Saved spread model to models/spread_prediction_model.joblib")

# ---------------------------------------------------------
# 10. Train Affected Road Geofencing Classifier (corridor prediction)
# ---------------------------------------------------------
print("\nTraining Affected Road Geofencing Classifier...")
# We will predict corridor_encoded based on location (latitude, longitude) and police_station_encoded
road_features = ['latitude', 'longitude', 'police_station_encoded', 'zone_encoded', 'gba_identifier_encoded']
y_train_road = train_df['corridor_encoded']
y_test_road = test_df['corridor_encoded']

road_model = RandomForestClassifier(n_estimators=100, random_state=42)
road_model.fit(train_df[road_features], y_train_road)

road_preds = road_model.predict(test_df[road_features])
print(f"Geofencing Road Model Test Accuracy: {accuracy_score(y_test_road, road_preds):.4f}")

joblib.dump(road_model, "models/geofencing_road_model.joblib")
print("Saved geofencing road model to models/geofencing_road_model.joblib")

# ---------------------------------------------------------
# 11. Plot Generation
# ---------------------------------------------------------
print("\nGenerating and saving evaluation plots...")

# 11.1 Model Performance Comparison Bar Chart
plt.figure(figsize=(10, 6))
metrics_plot = results_df[['accuracy', 'f1', 'auc']].reset_index().melt(id_vars='index')
sns.barplot(data=metrics_plot, x='index', y='value', hue='variable', palette='viridis')
plt.title("Model Comparison on 5-Fold Cross Validation", fontsize=14, fontweight='bold')
plt.xlabel("Model Name", fontsize=12)
plt.ylabel("Score", fontsize=12)
plt.ylim(0, 1.05)
plt.legend(title="Metric")
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.savefig("plots/model_comparison.png", dpi=300)
plt.close()

# 11.2 ROC Curves for Held-out Test Set
plt.figure(figsize=(8, 6))
# Tuned model
probs_tuned = tuned_model.predict_proba(X_test)[:, 1]
fpr_t, tpr_t, _ = roc_curve(y_test, probs_tuned)
auc_t = roc_auc_score(y_test, probs_tuned)
plt.plot(fpr_t, tpr_t, label=f"Tuned {best_model_name} (AUC = {auc_t:.4f})", lw=2)

# Ensemble
probs_ens = ensemble.predict_proba(X_test)[:, 1]
fpr_e, tpr_e, _ = roc_curve(y_test, probs_ens)
auc_e = roc_auc_score(y_test, probs_ens)
plt.plot(fpr_e, tpr_e, label=f"Voting Ensemble (AUC = {auc_e:.4f})", lw=2, linestyle='--')

plt.plot([0, 1], [0, 1], color='gray', linestyle=':', lw=1)
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate', fontsize=12)
plt.ylabel('True Positive Rate', fontsize=12)
plt.title('ROC Curves on Held-Out Test Set', fontsize=14, fontweight='bold')
plt.legend(loc="lower right")
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.savefig("plots/roc_curves.png", dpi=300)
plt.close()

# 11.3 Feature Importance for the Best Classifier (using Tuned model or RandomForest/XGB/LGB)
# Voting Classifier does not have feature_importances_ directly, so we use one of the underlying tree models
importance_model = tuned_model
if hasattr(importance_model, 'feature_importances_'):
    importances = importance_model.feature_importances_
    indices = np.argsort(importances)[::-1]
    
    plt.figure(figsize=(10, 8))
    sns.barplot(x=importances[indices], y=np.array(features)[indices], palette='mako')
    plt.title("Feature Importance - Traffic Severity Prediction", fontsize=14, fontweight='bold')
    plt.xlabel("Importance Score", fontsize=12)
    plt.ylabel("Features", fontsize=12)
    plt.tight_layout()
    plt.savefig("plots/feature_importance.png", dpi=300)
    plt.close()
elif hasattr(importance_model, 'get_feature_importance'): # CatBoost
    importances = importance_model.get_feature_importance()
    indices = np.argsort(importances)[::-1]
    
    plt.figure(figsize=(10, 8))
    sns.barplot(x=importances[indices], y=np.array(features)[indices], palette='mako')
    plt.title("Feature Importance - Traffic Severity Prediction", fontsize=14, fontweight='bold')
    plt.xlabel("Importance Score (CatBoost)", fontsize=12)
    plt.ylabel("Features", fontsize=12)
    plt.tight_layout()
    plt.savefig("plots/feature_importance.png", dpi=300)
    plt.close()

# 11.4 Confusion Matrix
best_preds = best_overall_model.predict(X_test)
cm = confusion_matrix(y_test, best_preds)
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Low Severity', 'High Severity'], yticklabels=['Low Severity', 'High Severity'])
plt.ylabel('Actual Label', fontsize=12)
plt.xlabel('Predicted Label', fontsize=12)
plt.title(f'Confusion Matrix - {best_overall_name}', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig("plots/confusion_matrix.png", dpi=300)
plt.close()

print("All plots generated and saved in plots/ folder.")
print("Pipeline complete!")
