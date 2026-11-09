import json

nb_path = 'IndoBERT_SNA_KEMENPU_Training_Pipeline.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

c10_source = ''.join(nb['cells'][10]['source'])

old_part = """    if os.path.exists(ENRICHED_PATH):
        src_df = pd.read_parquet(ENRICHED_PATH)
    else:
        src_df = pd.read_csv(MASTER_PATH, low_memory=False)

    col = 'predicted_sentiment' if 'predicted_sentiment' in src_df.columns else 'sentiment_name'
    sub_dfs = []
    for s_name, s_lbl in [('Negatif', 0), ('Netral', 1), ('Positif', 2)]:
        match = src_df[src_df[col] == s_name]
        n_take = min(8000, len(match))
        sub = match.sample(n=n_take, random_state=42)[['cleaned_content']].copy()
        sub['sentiment'] = s_name
        sub['label'] = s_lbl
        sub_dfs.append(sub)

    train_data = pd.concat(sub_dfs).sample(frac=1, random_state=42).reset_index(drop=True)
    train_data.columns = ['text', 'sentiment', 'label']

# Pembersihan data
train_data = train_data.dropna(subset=['text'])
train_data['text'] = train_data['text'].astype(str)
train_data = train_data[train_data['text'].str.strip().str.len() > 5]

print(f"\\n📊 Total data latih IndoBERT: {len(train_data):,} baris")
print(train_data['sentiment'].value_counts().to_string())

# Stratified Split 80/10/10
train_df, temp_df = train_test_split(train_data, test_size=0.2, random_state=42, stratify=train_data['label'])
val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42, stratify=temp_df['label'])
print(f"Split: Train={len(train_df):,}, Val={len(val_df):,}, Test={len(test_df):,}")"""

new_part = """    train_csv_path = os.path.join(DRIVE_DIR, 'train.csv')
    val_csv_path = os.path.join(DRIVE_DIR, 'val.csv')
    test_csv_path = os.path.join(DRIVE_DIR, 'test.csv')
    has_presplit_sent = os.path.exists(train_csv_path) and os.path.exists(val_csv_path) and os.path.exists(test_csv_path)

    if has_presplit_sent:
        print("✅ Memuat dataset sentimen langsung dari train/val/test CSV...")
        train_df = pd.read_csv(train_csv_path)
        val_df = pd.read_csv(val_csv_path)
        test_df = pd.read_csv(test_csv_path)
        for df_s in [train_df, val_df, test_df]:
            if 'cleaned_content' in df_s.columns and 'text' not in df_s.columns:
                df_s.rename(columns={'cleaned_content': 'text'}, inplace=True)
            if 'sentiment_label' in df_s.columns and 'label' not in df_s.columns:
                df_s.rename(columns={'sentiment_label': 'label'}, inplace=True)
        print(f"Split: Train={len(train_df):,}, Val={len(val_df):,}, Test={len(test_df):,}")
    else:
        if os.path.exists(ENRICHED_PATH):
            src_df = pd.read_parquet(ENRICHED_PATH)
        else:
            src_df = pd.read_csv(MASTER_PATH, low_memory=False)

        col = None
        for candidate in ['predicted_sentiment', 'sentiment_name', 'sentiment']:
            if candidate in src_df.columns:
                col = candidate
                break

        if col:
            sub_dfs = []
            for s_name, s_lbl in [('Negatif', 0), ('Netral', 1), ('Positif', 2)]:
                match = src_df[src_df[col] == s_name]
                n_take = min(8000, len(match))
                if n_take > 0:
                    sub = match.sample(n=n_take, random_state=42)[['cleaned_content']].copy()
                    sub['sentiment'] = s_name
                    sub['label'] = s_lbl
                    sub_dfs.append(sub)
            train_data = pd.concat(sub_dfs).sample(frac=1, random_state=42).reset_index(drop=True)
            train_data.columns = ['text', 'sentiment', 'label']
        elif not gold_df.empty and 'gemini_sentiment' in gold_df.columns:
            print("Menggunakan data anotasi Gemini (gold_df) sebagai dataset latih...")
            train_data = gold_df[['cleaned_content', 'gemini_sentiment', 'sentiment_label']].copy()
            train_data.columns = ['text', 'sentiment', 'label']
        else:
            raise ValueError("Dataset sentimen tidak memiliki label valid untuk training!")

        train_data = train_data.dropna(subset=['text'])
        train_data['text'] = train_data['text'].astype(str)
        train_data = train_data[train_data['text'].str.strip().str.len() > 5]

        print(f"\\n📊 Total data latih IndoBERT: {len(train_data):,} baris")
        print(train_data['sentiment'].value_counts().to_string())

        train_df, temp_df = train_test_split(train_data, test_size=0.2, random_state=42, stratify=train_data['label'])
        val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42, stratify=temp_df['label'])
        print(f"Split: Train={len(train_df):,}, Val={len(val_df):,}, Test={len(test_df):,}")"""

if old_part in c10_source:
    c10_source = c10_source.replace(old_part, new_part)
    nb['cells'][10]['source'] = [l + '\n' for l in c10_source.split('\n')]
    if nb['cells'][10]['source'][-1] == '\n':
        nb['cells'][10]['source'] = nb['cells'][10]['source'][:-1]
    with open(nb_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("SUCCESS: Patched Cell 10 successfully!")
else:
    print("WARNING: old_part not found in Cell 10!")

