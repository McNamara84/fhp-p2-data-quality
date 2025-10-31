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
# ÜBERSICHTS-DIAGRAMM: ISBN-Verteilung
# Zeigt wie viele Datensätze eine ISBN haben vs. keine ISBN
# ============================================================

isbn_overview_data <- data.frame(
  Kategorie = factor(
    c("Datensätze gesamt", "Davon mit ISBN", "Davon ohne ISBN"),
    levels = c("Datensätze gesamt", "Davon mit ISBN", "Davon ohne ISBN")
  ),
  Anzahl = c(
    total_records_in_xml,
    records_with_isbn,
    total_records_in_xml - records_with_isbn
  )
)

p_overview <- ggplot(isbn_overview_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  geom_text(
    aes(label = paste0("(", round(Anzahl / total_records_in_xml * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(
    name = "Kategorie",
    values = c(
      "Datensätze gesamt" = "#95a5a6",
      "Davon mit ISBN" = "#667eea",
      "Davon ohne ISBN" = "#e74c3c"
    )
  ) +
  labs(
    title = "Übersicht: ISBN-Verfügbarkeit im Gesamtdatenbestand",
    subtitle = "Verteilung der Datensätze mit und ohne ISBN",
    x = "Datensatz-Kategorie",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold", margin = margin(t = 10)),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "right",
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 11),
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    plot.margin = margin(20, 20, 20, 20)
  ) +
  scale_y_continuous(
    labels = function(x) format(x, big.mark = ".", decimal.mark = ",", scientific = FALSE),
    expand = expansion(mult = c(0, 0.15))
  )

output_file_overview <- file.path(output_dir, "isbn_overview.png")
ggsave(output_file_overview, plot = p_overview, width = 12, height = 10, dpi = 300, bg = "white")
cat("✓ Diagramm erstellt:", output_file_overview, "\n")

# ============================================================
# Diagramm 1: Title - Balkendiagramm
# ============================================================

# Daten für Title
title_stats <- field_stats$Title

# Berechne Werte für die 3 Balken (ohne "Gesamt")
# MIT ISBN ist nun die 100%-Basis
records_with_isbn_val <- records_with_isbn  # Datensätze mit ISBN (neue Basis = 100%)
empty_before <- title_stats$empty_before    # Leere Title-Felder vorher
filled_after <- title_stats$filled_after    # Befüllte Title-Felder

# Erstelle Data Frame
title_data <- data.frame(
  Kategorie = factor(
    c("Mit ISBN", "Leer vorher", "Befüllt"),
    levels = c("Mit ISBN", "Leer vorher", "Befüllt")
  ),
  Anzahl = c(records_with_isbn_val, empty_before, filled_after)
)

# Balkendiagramm erstellen
p <- ggplot(title_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  # Zahlen über den Balken - für kleine Werte prominenter anzeigen
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  # Prozentangaben für ALLE Balken (relativ zu "Mit ISBN")
  geom_text(
    aes(label = paste0("(", round(Anzahl / records_with_isbn_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(
    name = "Kategorie",
    values = c(
      "Mit ISBN" = "#667eea",
      "Leer vorher" = "#e74c3c",
      "Befüllt" = "#27ae60"
    )
  ) +
  labs(
    title = "Metadatenelement: Title",
    subtitle = "Anreicherung leerer Felder",
    x = "Anreicherungs-Kategorie",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold", margin = margin(t = 10)),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "right",
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 11),
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

# Erstelle Data Frame (ohne "Gesamt")
title_corrections_data <- data.frame(
  Kategorie = factor(
    c("Mit ISBN", "Fehlerhafte Ansetzung", "Ansetzung korrigiert"),
    levels = c("Mit ISBN", "Fehlerhafte Ansetzung", "Ansetzung korrigiert")
  ),
  Anzahl = c(records_with_isbn_val, abbreviations_and_errors_before, abbreviations_and_errors_fixed)
)

# Balkendiagramm erstellen
p2 <- ggplot(title_corrections_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  # Zahlen über den Balken
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  # Prozentangaben für ALLE Balken (relativ zu "Mit ISBN")
  geom_text(
    aes(label = paste0("(", round(Anzahl / records_with_isbn_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(
    name = "Kategorie",
    values = c(
      "Mit ISBN" = "#667eea",
      "Fehlerhafte Ansetzung" = "#e67e22",
      "Ansetzung korrigiert" = "#27ae60"
    )
  ) +
  labs(
    title = "Metadatenelement: Title",
    subtitle = "Ausschreiben von Abkürzungen und Fehlerkorrekturen",
    x = "Anreicherungs-Kategorie",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold", margin = margin(t = 10)),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "right",
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 11),
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

# Erstelle Data Frame (ohne "Gesamt")
title_total_impact_data <- data.frame(
  Kategorie = factor(
    c("Mit ISBN", "Angereichert"),
    levels = c("Mit ISBN", "Angereichert")
  ),
  Anzahl = c(records_with_isbn_val, total_enriched)
)

# Balkendiagramm erstellen
p3 <- ggplot(title_total_impact_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  # Zahlen über den Balken
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  # Prozentangaben für ALLE Balken (relativ zu "Mit ISBN")
  geom_text(
    aes(label = paste0("(", round(Anzahl / records_with_isbn_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(
    name = "Kategorie",
    values = c(
      "Mit ISBN" = "#667eea",
      "Angereichert" = "#27ae60"
    )
  ) +
  labs(
    title = "Metadatenelement: Title",
    subtitle = "Gesamtwirkung der Anreicherung",
    x = "Anreicherungs-Kategorie",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold", margin = margin(t = 10)),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "right",
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 11),
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
    c("Mit ISBN", "Leer vorher", "Befüllt"),
    levels = c("Mit ISBN", "Leer vorher", "Befüllt")
  ),
  Anzahl = c(records_with_isbn_val, authors_empty_before, authors_filled_after)
)

p4 <- ggplot(authors_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  geom_text(
    aes(label = paste0("(", round(Anzahl / records_with_isbn_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(
    name = "Kategorie",
    values = c(
      "Mit ISBN" = "#667eea",
      "Leer vorher" = "#e74c3c",
      "Befüllt" = "#27ae60"
    )
  ) +
  labs(
    title = "Metadatenelement: Authors",
    subtitle = "Anreicherung leerer Felder",
    x = "Anreicherungs-Kategorie",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold", margin = margin(t = 10)),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "right",
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 11),
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
    c("Mit ISBN", "Fehlerhafte Ansetzung", "Ansetzung korrigiert"),
    levels = c("Mit ISBN", "Fehlerhafte Ansetzung", "Ansetzung korrigiert")
  ),
  Anzahl = c(records_with_isbn_val, authors_abbrev_and_errors, authors_abbrev_and_errors)
)

p5 <- ggplot(authors_corrections_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  geom_text(
    aes(label = paste0("(", round(Anzahl / records_with_isbn_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(
    name = "Kategorie",
    values = c(
      "Mit ISBN" = "#667eea",
      "Fehlerhafte Ansetzung" = "#e67e22",
      "Ansetzung korrigiert" = "#27ae60"
    )
  ) +
  labs(
    title = "Metadatenelement: Authors",
    subtitle = "Ausschreiben von Abkürzungen und Fehlerkorrekturen",
    x = "Anreicherungs-Kategorie",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold", margin = margin(t = 10)),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "right",
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 11),
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
    c("Mit ISBN", "Angereichert"),
    levels = c("Mit ISBN", "Angereichert")
  ),
  Anzahl = c(records_with_isbn_val, authors_total_enriched)
)

p6 <- ggplot(authors_total_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  geom_text(
    aes(label = paste0("(", round(Anzahl / records_with_isbn_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(
    name = "Kategorie",
    values = c(
      "Mit ISBN" = "#667eea",
      "Angereichert" = "#27ae60"
    )
  ) +
  labs(
    title = "Metadatenelement: Authors",
    subtitle = "Gesamtwirkung der Anreicherung",
    x = "Anreicherungs-Kategorie",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold", margin = margin(t = 10)),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "right",
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 11),
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
# PUBLISHER STATISTICS
# ============================================================

publisher_stats <- field_stats$Publisher

# ============================================================
# Diagramm 7: Publisher - Leere Felder befüllen
# ============================================================

publisher_empty_before <- publisher_stats$empty_before
publisher_filled_after <- publisher_stats$filled_after

publisher_enrichment_data <- data.frame(
  Kategorie = factor(
    c("Mit ISBN", "Leer vorher", "Befüllt"),
    levels = c("Mit ISBN", "Leer vorher", "Befüllt")
  ),
  Anzahl = c(records_with_isbn_val, publisher_empty_before, publisher_filled_after)
)

p7 <- ggplot(publisher_enrichment_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  geom_text(
    aes(label = paste0("(", round(Anzahl / records_with_isbn_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(
    name = "Kategorie",
    values = c(
      "Mit ISBN" = "#667eea",
      "Leer vorher" = "#e74c3c",
      "Befüllt" = "#27ae60"
    )
  ) +
  labs(
    title = "Metadatenelement: Publisher",
    subtitle = "Befüllen leerer Felder",
    x = "Anreicherungs-Kategorie",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold", margin = margin(t = 10)),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "right",
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 11),
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    plot.margin = margin(20, 20, 20, 20)
  ) +
  scale_y_continuous(
    labels = function(x) format(x, big.mark = ".", decimal.mark = ",", scientific = FALSE),
    expand = expansion(mult = c(0, 0.15))
  )

output_file_7 <- file.path(output_dir, "publisher_enrichment.png")
ggsave(output_file_7, plot = p7, width = 12, height = 10, dpi = 300, bg = "white")
cat("✓ Diagramm erstellt:", output_file_7, "\n")

# ============================================================
# Diagramm 8: Publisher - Abkürzungen und Korrekturen
# ============================================================

publisher_abbreviations <- publisher_stats$abbreviation_replaced
publisher_corrections <- publisher_stats$corrected
publisher_abbrev_and_errors <- publisher_abbreviations + publisher_corrections

publisher_corrections_data <- data.frame(
  Kategorie = factor(
    c("Mit ISBN", "Fehlerhafte Ansetzung", "Ansetzung korrigiert"),
    levels = c("Mit ISBN", "Fehlerhafte Ansetzung", "Ansetzung korrigiert")
  ),
  Anzahl = c(records_with_isbn_val, publisher_abbrev_and_errors, publisher_abbrev_and_errors)
)

p8 <- ggplot(publisher_corrections_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  geom_text(
    aes(label = paste0("(", round(Anzahl / records_with_isbn_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(
    name = "Kategorie",
    values = c(
      "Mit ISBN" = "#667eea",
      "Fehlerhafte Ansetzung" = "#e67e22",
      "Ansetzung korrigiert" = "#27ae60"
    )
  ) +
  labs(
    title = "Metadatenelement: Publisher",
    subtitle = "Ausschreiben von Abkürzungen und Fehlerkorrekturen",
    x = "Anreicherungs-Kategorie",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold", margin = margin(t = 10)),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "right",
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 11),
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    plot.margin = margin(20, 20, 20, 20)
  ) +
  scale_y_continuous(
    labels = function(x) format(x, big.mark = ".", decimal.mark = ",", scientific = FALSE),
    expand = expansion(mult = c(0, 0.15))
  )

output_file_8 <- file.path(output_dir, "publisher_corrections.png")
ggsave(output_file_8, plot = p8, width = 12, height = 10, dpi = 300, bg = "white")
cat("✓ Diagramm erstellt:", output_file_8, "\n")

# ============================================================
# Diagramm 9: Publisher - Gesamtwirkung
# ============================================================

publisher_total_enriched <- publisher_filled_after + publisher_abbrev_and_errors

publisher_total_data <- data.frame(
  Kategorie = factor(
    c("Mit ISBN", "Angereichert"),
    levels = c("Mit ISBN", "Angereichert")
  ),
  Anzahl = c(records_with_isbn_val, publisher_total_enriched)
)

p9 <- ggplot(publisher_total_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  geom_text(
    aes(label = paste0("(", round(Anzahl / records_with_isbn_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(
    name = "Kategorie",
    values = c(
      "Mit ISBN" = "#667eea",
      "Angereichert" = "#27ae60"
    )
  ) +
  labs(
    title = "Metadatenelement: Publisher",
    subtitle = "Gesamtwirkung der Anreicherung",
    x = "Anreicherungs-Kategorie",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold", margin = margin(t = 10)),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "right",
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 11),
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    plot.margin = margin(20, 20, 20, 20)
  ) +
  scale_y_continuous(
    labels = function(x) format(x, big.mark = ".", decimal.mark = ",", scientific = FALSE),
    expand = expansion(mult = c(0, 0.15))
  )

output_file_9 <- file.path(output_dir, "publisher_total_impact.png")
ggsave(output_file_9, plot = p9, width = 12, height = 10, dpi = 300, bg = "white")
cat("✓ Diagramm erstellt:", output_file_9, "\n")

# ============================================================
# YEAR STATISTICS
# ============================================================

year_stats <- field_stats$Year

# ============================================================
# Diagramm 10: Year - Leere Felder befüllen
# ============================================================

year_empty_before <- year_stats$empty_before
year_filled_after <- year_stats$filled_after

year_enrichment_data <- data.frame(
  Kategorie = factor(
    c("Mit ISBN", "Leer vorher", "Befüllt"),
    levels = c("Mit ISBN", "Leer vorher", "Befüllt")
  ),
  Anzahl = c(records_with_isbn_val, year_empty_before, year_filled_after)
)

p10 <- ggplot(year_enrichment_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  geom_text(
    aes(label = paste0("(", round(Anzahl / records_with_isbn_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(
    name = "Kategorie",
    values = c(
      "Mit ISBN" = "#667eea",
      "Leer vorher" = "#e74c3c",
      "Befüllt" = "#27ae60"
    )
  ) +
  labs(
    title = "Metadatenelement: Year",
    subtitle = "Befüllen leerer Felder",
    x = "Anreicherungs-Kategorie",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold", margin = margin(t = 10)),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "right",
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 11),
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    plot.margin = margin(20, 20, 20, 20)
  ) +
  scale_y_continuous(
    labels = function(x) format(x, big.mark = ".", decimal.mark = ",", scientific = FALSE),
    expand = expansion(mult = c(0, 0.15))
  )

output_file_10 <- file.path(output_dir, "year_enrichment.png")
ggsave(output_file_10, plot = p10, width = 12, height = 10, dpi = 300, bg = "white")
cat("✓ Diagramm erstellt:", output_file_10, "\n")

# ============================================================
# Diagramm 11: Year - Abkürzungen und Korrekturen
# ============================================================

year_abbreviations <- year_stats$abbreviation_replaced
year_corrections <- year_stats$corrected
year_abbrev_and_errors <- year_abbreviations + year_corrections

year_corrections_data <- data.frame(
  Kategorie = factor(
    c("Mit ISBN", "Fehlerhafte Ansetzung", "Ansetzung korrigiert"),
    levels = c("Mit ISBN", "Fehlerhafte Ansetzung", "Ansetzung korrigiert")
  ),
  Anzahl = c(records_with_isbn_val, year_abbrev_and_errors, year_abbrev_and_errors)
)

p11 <- ggplot(year_corrections_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  geom_text(
    aes(label = paste0("(", round(Anzahl / records_with_isbn_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(
    name = "Kategorie",
    values = c(
      "Mit ISBN" = "#667eea",
      "Fehlerhafte Ansetzung" = "#e67e22",
      "Ansetzung korrigiert" = "#27ae60"
    )
  ) +
  labs(
    title = "Metadatenelement: Year",
    subtitle = "Ausschreiben von Abkürzungen und Fehlerkorrekturen",
    x = "Anreicherungs-Kategorie",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold", margin = margin(t = 10)),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "right",
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 11),
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    plot.margin = margin(20, 20, 20, 20)
  ) +
  scale_y_continuous(
    labels = function(x) format(x, big.mark = ".", decimal.mark = ",", scientific = FALSE),
    expand = expansion(mult = c(0, 0.15))
  )

output_file_11 <- file.path(output_dir, "year_corrections.png")
ggsave(output_file_11, plot = p11, width = 12, height = 10, dpi = 300, bg = "white")
cat("✓ Diagramm erstellt:", output_file_11, "\n")

# ============================================================
# Diagramm 12: Year - Gesamtwirkung
# ============================================================

year_total_enriched <- year_filled_after + year_abbrev_and_errors

year_total_data <- data.frame(
  Kategorie = factor(
    c("Mit ISBN", "Angereichert"),
    levels = c("Mit ISBN", "Angereichert")
  ),
  Anzahl = c(records_with_isbn_val, year_total_enriched)
)

p12 <- ggplot(year_total_data, aes(x = Kategorie, y = Anzahl, fill = Kategorie)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_text(aes(label = format(Anzahl, big.mark = ".", decimal.mark = ",")), 
            vjust = -0.5, size = 5, fontface = "bold", color = "black") +
  geom_text(
    aes(label = paste0("(", round(Anzahl / records_with_isbn_val * 100, 2), "%)")),
    vjust = 1.5, size = 4, color = "gray30"
  ) +
  scale_fill_manual(
    name = "Kategorie",
    values = c(
      "Mit ISBN" = "#667eea",
      "Angereichert" = "#27ae60"
    )
  ) +
  labs(
    title = "Metadatenelement: Year",
    subtitle = "Gesamtwirkung der Anreicherung",
    x = "Anreicherungs-Kategorie",
    y = "Anzahl Datensätze"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "gray40"),
    axis.text.x = element_text(size = 12, face = "bold"),
    axis.text.y = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold", margin = margin(t = 10)),
    axis.title.y = element_text(size = 13, face = "bold"),
    legend.position = "right",
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 11),
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    plot.margin = margin(20, 20, 20, 20)
  ) +
  scale_y_continuous(
    labels = function(x) format(x, big.mark = ".", decimal.mark = ",", scientific = FALSE),
    expand = expansion(mult = c(0, 0.15))
  )

output_file_12 <- file.path(output_dir, "year_total_impact.png")
ggsave(output_file_12, plot = p12, width = 12, height = 10, dpi = 300, bg = "white")
cat("✓ Diagramm erstellt:", output_file_12, "\n")

cat("\n✓ Alle Diagramme erfolgreich erstellt!\n")
