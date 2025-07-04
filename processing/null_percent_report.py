from processing.utils import get_db_connection
import pandas as pd
import os

def null_percent_report():
    """
    Génère un rapport sur le pourcentage de valeurs NULL par colonne et par ligne.

    Args:
        None
    Returns:
        None: Affiche des informations dans la console et sauvegarde un rapport CSV.
    """
    conn = get_db_connection()
    if conn is None:
        print("Connexion à la base impossible.")
        return
    cur = conn.cursor()
    # on récupère la liste des tables de la base
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE';
    """)
    tables = [row[0] for row in cur.fetchall()]
    results = []
    for table in tables:
        # on récupère la liste des colonnes pour chaque table
        cur.execute(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
        """, (table,))
        columns = [row[0] for row in cur.fetchall()]
        # on compte le nombre total de lignes de la table
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        total_row = cur.fetchone()
        total = total_row[0] if total_row and total_row[0] is not None else 0
        for col in columns:
            # on compte le nombre de valeurs NULL pour chaque colonne
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL;")
            n_null_row = cur.fetchone()
            n_null = n_null_row[0] if n_null_row and n_null_row[0] is not None else 0
            percent_null = 100 * n_null / total if total else 0
            results.append({
                'table': table,
                'column': col,
                'percent_null': round(percent_null, 2)
            })
    # on crée un DataFrame pour trier et analyser les résultats
    df = pd.DataFrame(results).sort_values(by=['table', 'percent_null'], ascending=[True, False])
    high_null = df[df['percent_null'] > 80]
    if not high_null.empty:
        print("Colonnes avec plus de 80% de valeurs NULL :")
        print(high_null.to_string(index=False))
    else:
        print("Aucune colonne avec plus de 80% de NULL.")
    ligne_null_stats = []
    for table in tables:
        # on récupère toutes les lignes de la table pour analyser le taux de NULL par ligne
        cur.execute(f"SELECT * FROM {table};")
        rows = cur.fetchall()
        if not rows or cur.description is None:
            print(f"Table {table}: aucune donnée.")
            ligne_null_stats.append({'table': table, 'percent_rows_80pct_null': 0.0, 'n_rows': 0, 'n_80pct_null': 0})
            continue
        colnames = [desc[0] for desc in cur.description]
        n_cols = len(colnames)
        n_80pct_empty = 0
        for row in rows:
            # on compte le nombre de valeurs NULL dans la ligne
            n_null_in_row = sum(1 for val in row if val is None)
            # on vérifie si la ligne a au moins 80% de valeurs NULL
            if n_cols > 0 and n_null_in_row / n_cols >= 0.8:
                n_80pct_empty += 1
        pct_80pct_empty = 100 * n_80pct_empty / len(rows) if rows else 0
        ligne_null_stats.append({
            'table': table,
            'percent_rows_80pct_null': round(pct_80pct_empty, 2),
            'n_rows': len(rows),
            'n_80pct_null': n_80pct_empty
        })
        print(f"Table {table}: {pct_80pct_empty:.2f}% des lignes ont au moins 80% de valeurs NULL ({n_80pct_empty}/{len(rows)})")
    # on fusionne les résultats colonne et ligne pour le rapport final
    df_ligne_null = pd.DataFrame(ligne_null_stats)
    merged_rows = []
    for _, row in df.iterrows():
        merged_rows.append({
            'table': row['table'],
            'column': row['column'],
            'percent_null': row['percent_null']
        })
    for _, row in df_ligne_null.iterrows():
        merged_rows.append({
            'table': row['table'],
            'column': None,
            'percent_null': row['percent_rows_80pct_null']
        })
    df_merged = pd.DataFrame(merged_rows)
    # on sauvegarde le rapport fusionné dans un fichier CSV
    output_path = os.path.join('docs', 'null_percent_report.csv')
    df_merged.to_csv(output_path, index=False)
    print(f"Rapport fusionné sauvegardé dans {output_path}")
    cur.close()
    conn.close()

if __name__ == '__main__':
    print("Génération du rapport de pourcentage de NULL...")
    null_percent_report()
    print("Rapport de pourcentage de NULL généré.")