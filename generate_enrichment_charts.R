#!/usr/bin/env Rscript
# -*- coding: utf-8 -*-
# Generiert Diagramme für die Anreicherungsstatistik

library(jsonlite)
library(ggplot2)

# Kommandozeilen-Argumente
args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 2) {
  cat("Verwendung: Rscript generate_enrichment_charts.R <stats_file.json> <output_dir>\n")
  quit(status = 1)
}

stats_file <- args[1]
output_dir <- args[2]

# Erstelle Output-Verzeichnis falls nicht vorhanden
if (!dir.exists(output_dir)) {
  dir.create(output_dir, recursive = TRUE)
}

# Lade JSON-Statistiken
cat("Lade Statistiken aus:", stats_file, "\n")
stats <- fromJSON(stats_file)

# Extrahiere relevante Daten
# WICHTIG: Die JSON enthält nicht die Gesamtzahl aller Records aus der XML!
# Wir müssen sie aus der XML-Datei oder als Konstante verwenden
distinct_isbns <- stats$metadata$total_records_in_file  # 544.879 eindeutige ISBNs
records_with_isbn <- stats$summary$processed_records     # 831.973 Datensätze mit ISBN
field_stats <- stats$field_statistics

# HARDCODED: Gesamtzahl Records aus voebvoll-20241027.xml (gezählt)
# Diese Zahl müsste eigentlich in metadata.total_records_in_xml stehen
total_records_in_xml <- 1264927  # Tatsächliche Anzahl <record> Tags

# ============================================================
# Diagramm 1: Title - Balkendiagramm
# ============================================================

# Daten für Title
title_stats <- field_stats$Title

# Berechne Werte für die 4 Balken
total_records_val <- total_records_in_xml  # ALLE Datensätze in XML
records_with_isbn_val <- records_with_isbn  # Datensätze mit ISBN (831.973)
empty_before <- title_stats$empty_before    # Leere Title-Felder vorher
filled_after <- title_stats$filled_after    # Befüllte Title-Felder

# Erstelle Data Frame
title_data <- data.frame(
  Kategorie = factor(
    c("Gesamt", "Mit ISBN", "Leer vorher", "Befüllt"),
    levels = c("Gesamt", "Mit ISBN", "Leer vorher", "Befüllt")
  ),
  Anzahl = c(total_records_val, records_with_isbn_val, empty_before, filled_after)
)

# Balkendiagramm erstellen
p <- ggplot(title_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 4, fontface = "bold") +
  scale_fill_manual(values = c(
    "Gesamt" = "#667eea",
    "Mit ISBN" = "#764ba2", 
    "Leer vorher" = "#e74c3c",
    "Befüllt" = "#27ae60"
  )) +
  labs(
    title = "Metadatenelement: Title",
    subtitle = "Anreicherung leerer Felder",
    x = "",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "none",
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    plot.margin = margin(20, 20, 20, 20)
  ) +
  scale_y_continuous(
    labels = function(x) format(x, big.mark = ".", decimal.mark = ",", scientific = FALSE),
    expand = expansion(mult = c(0, 0.1))
  )

# Speichern als PNG (hohe Auflösung für wissenschaftliche Arbeit)
output_file <- file.path(output_dir, "title_enrichment.png")
ggsave(
  output_file,
  plot = p,
  width = 10,
  height = 6,
  dpi = 300,
  bg = "white"
)

cat("✓ Diagramm erstellt:", output_file, "\n")

# ============================================================
# Weitere Diagramme können hier hinzugefügt werden
# ============================================================

cat("\n✓ Alle Diagramme erfolgreich erstellt!\n")
