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
  # Zahlen über den Balken - für kleine Werte prominenter anzeigen
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  # Prozentangaben für ALLE Balken (relativ zur Gesamtzahl)
  geom_text(
    aes(label = paste0("(", round(Anzahl / total_records_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
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
    expand = expansion(mult = c(0, 0.15))  # Mehr Platz oben für Labels
  )

# Speichern als PNG (hohe Auflösung + größere Höhe)
output_file <- file.path(output_dir, "title_enrichment.png")
ggsave(
  output_file,
  plot = p,
  width = 12,   # Breiter
  height = 10,  # Noch höher (war 8)
  dpi = 300,
  bg = "white"
)

cat("✓ Diagramm erstellt:", output_file, "\n")

# ============================================================
# Diagramm 2: Title - Abkürzungen und Korrekturen
# ============================================================

# Berechne Anzahl der Abkürzungen und Korrekturen
abbreviations_before <- title_stats$abbreviation_replaced  # Abkürzungen die ersetzt wurden
corrections <- title_stats$corrected  # Fehler die korrigiert wurden

# Kombiniere beide für "vorher" und "nachher"
abbreviations_and_errors_before <- abbreviations_before + corrections
abbreviations_and_errors_fixed <- abbreviations_before + corrections  # Beide wurden behoben

# Erstelle Data Frame
title_corrections_data <- data.frame(
  Kategorie = factor(
    c("Gesamt", "Mit ISBN", "Abgekürzt/Fehler vorher", "Ausgeschrieben/korrigiert"),
    levels = c("Gesamt", "Mit ISBN", "Abgekürzt/Fehler vorher", "Ausgeschrieben/korrigiert")
  ),
  Anzahl = c(total_records_val, records_with_isbn_val, abbreviations_and_errors_before, abbreviations_and_errors_fixed)
)

# Balkendiagramm erstellen
p2 <- ggplot(title_corrections_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  # Zahlen über den Balken
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  # Prozentangaben für ALLE Balken (relativ zur Gesamtzahl)
  geom_text(
    aes(label = paste0("(", round(Anzahl / total_records_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(values = c(
    "Gesamt" = "#667eea",
    "Mit ISBN" = "#764ba2", 
    "Abgekürzt/Fehler vorher" = "#e67e22",
    "Ausgeschrieben/korrigiert" = "#27ae60"
  )) +
  labs(
    title = "Metadatenelement: Title",
    subtitle = "Ausschreiben von Abkürzungen und Fehlerkorrekturen",
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
    expand = expansion(mult = c(0, 0.15))
  )

# Speichern als PNG
output_file_2 <- file.path(output_dir, "title_corrections.png")
ggsave(
  output_file_2,
  plot = p2,
  width = 12,
  height = 10,
  dpi = 300,
  bg = "white"
)

cat("✓ Diagramm erstellt:", output_file_2, "\n")

# ============================================================
# Diagramm 3: Title - Gesamtwirkung der Anreicherung
# ============================================================

# Berechne Gesamtzahl angereicherter Datensätze
total_enriched <- filled_after + abbreviations_and_errors_fixed  # 265 + 84.782

# Erstelle Data Frame
title_total_impact_data <- data.frame(
  Kategorie = factor(
    c("Gesamt", "Mit ISBN", "Angereichert"),
    levels = c("Gesamt", "Mit ISBN", "Angereichert")
  ),
  Anzahl = c(total_records_val, records_with_isbn_val, total_enriched)
)

# Balkendiagramm erstellen
p3 <- ggplot(title_total_impact_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  # Zahlen über den Balken
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  # Prozentangaben für ALLE Balken (relativ zur Gesamtzahl)
  geom_text(
    aes(label = paste0("(", round(Anzahl / total_records_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(values = c(
    "Gesamt" = "#667eea",
    "Mit ISBN" = "#764ba2", 
    "Angereichert" = "#27ae60"
  )) +
  labs(
    title = "Metadatenelement: Title",
    subtitle = "Gesamtwirkung der Anreicherung",
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
    expand = expansion(mult = c(0, 0.15))
  )

# Speichern als PNG
output_file_3 <- file.path(output_dir, "title_total_impact.png")
ggsave(
  output_file_3,
  plot = p3,
  width = 12,
  height = 10,
  dpi = 300,
  bg = "white"
)

cat("✓ Diagramm erstellt:", output_file_3, "\n")

# ============================================================
# METADATENELEMENT: AUTHORS
# ============================================================

# Daten für Authors
authors_stats <- field_stats$Authors

# ============================================================
# Diagramm 4: Authors - Leere Felder befüllen
# ============================================================

authors_empty_before <- authors_stats$empty_before
authors_filled_after <- authors_stats$filled_after

authors_data <- data.frame(
  Kategorie = factor(
    c("Gesamt", "Mit ISBN", "Leer vorher", "Befüllt"),
    levels = c("Gesamt", "Mit ISBN", "Leer vorher", "Befüllt")
  ),
  Anzahl = c(total_records_val, records_with_isbn_val, authors_empty_before, authors_filled_after)
)

p4 <- ggplot(authors_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  geom_text(
    aes(label = paste0("(", round(Anzahl / total_records_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(values = c(
    "Gesamt" = "#667eea",
    "Mit ISBN" = "#764ba2", 
    "Leer vorher" = "#e74c3c",
    "Befüllt" = "#27ae60"
  )) +
  labs(
    title = "Metadatenelement: Authors",
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
    expand = expansion(mult = c(0, 0.15))
  )

output_file_4 <- file.path(output_dir, "authors_enrichment.png")
ggsave(output_file_4, plot = p4, width = 12, height = 10, dpi = 300, bg = "white")
cat("✓ Diagramm erstellt:", output_file_4, "\n")

# ============================================================
# Diagramm 5: Authors - Abkürzungen und Korrekturen
# ============================================================

authors_abbreviations <- authors_stats$abbreviation_replaced
authors_corrections <- authors_stats$corrected
authors_abbrev_and_errors <- authors_abbreviations + authors_corrections

authors_corrections_data <- data.frame(
  Kategorie = factor(
    c("Gesamt", "Mit ISBN", "Abgekürzt/Fehler vorher", "Ausgeschrieben/korrigiert"),
    levels = c("Gesamt", "Mit ISBN", "Abgekürzt/Fehler vorher", "Ausgeschrieben/korrigiert")
  ),
  Anzahl = c(total_records_val, records_with_isbn_val, authors_abbrev_and_errors, authors_abbrev_and_errors)
)

p5 <- ggplot(authors_corrections_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  geom_text(
    aes(label = paste0("(", round(Anzahl / total_records_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(values = c(
    "Gesamt" = "#667eea",
    "Mit ISBN" = "#764ba2", 
    "Abgekürzt/Fehler vorher" = "#e67e22",
    "Ausgeschrieben/korrigiert" = "#27ae60"
  )) +
  labs(
    title = "Metadatenelement: Authors",
    subtitle = "Ausschreiben von Abkürzungen und Fehlerkorrekturen",
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
    expand = expansion(mult = c(0, 0.15))
  )

output_file_5 <- file.path(output_dir, "authors_corrections.png")
ggsave(output_file_5, plot = p5, width = 12, height = 10, dpi = 300, bg = "white")
cat("✓ Diagramm erstellt:", output_file_5, "\n")

# ============================================================
# Diagramm 6: Authors - Gesamtwirkung
# ============================================================

authors_total_enriched <- authors_filled_after + authors_abbrev_and_errors

authors_total_data <- data.frame(
  Kategorie = factor(
    c("Gesamt", "Mit ISBN", "Angereichert"),
    levels = c("Gesamt", "Mit ISBN", "Angereichert")
  ),
  Anzahl = c(total_records_val, records_with_isbn_val, authors_total_enriched)
)

p6 <- ggplot(authors_total_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  geom_text(
    aes(label = paste0("(", round(Anzahl / total_records_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(values = c(
    "Gesamt" = "#667eea",
    "Mit ISBN" = "#764ba2", 
    "Angereichert" = "#27ae60"
  )) +
  labs(
    title = "Metadatenelement: Authors",
    subtitle = "Gesamtwirkung der Anreicherung",
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
    expand = expansion(mult = c(0, 0.15))
  )

output_file_6 <- file.path(output_dir, "authors_total_impact.png")
ggsave(output_file_6, plot = p6, width = 12, height = 10, dpi = 300, bg = "white")
cat("✓ Diagramm erstellt:", output_file_6, "\n")

# ============================================================
# Weitere Diagramme können hier hinzugefügt werden
# ============================================================

cat("\n✓ Alle Diagramme erfolgreich erstellt!\n")
