import os
import glob
import time
import threading
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.dialog import MDDialog
from groq import Groq

# Librerie ReportLab per generazione PDF nativa
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, HRFlowable
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib import colors

MIA_API_KEY = "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"

class TrascrizioneScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.file_selezionato = ""
        self.pdf_generato = ""
        
        layout = MDBoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Titolo
        layout.add_widget(MDLabel(
            text="Trascrizione Lezioni Android",
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=40
        ))
        
        # Selezione File
        self.btn_file = MDRaisedButton(
            text="Seleziona File Audio/Video",
            pos_hint={'center_x': 0.5},
            on_release=self.apri_file_manager
        )
        layout.add_widget(self.btn_file)
        
        self.lbl_file = MDLabel(
            text="Nessun file selezionato",
            halign="center",
            theme_text_color="Hint",
            size_hint_y=None,
            height=30
        )
        layout.add_widget(self.lbl_file)
        
        # Barra di Stato
        self.lbl_status = MDLabel(
            text="Stato: In attesa...",
            halign="center",
            size_hint_y=None,
            height=30
        )
        layout.add_widget(self.lbl_status)
        
        self.progress = MDProgressBar(value=0, pos_hint={'center_x': 0.5})
        layout.add_widget(self.progress)
        
        # Pulsante Avvio
        self.btn_avvia = MDRaisedButton(
            text="🚀 Avvia Trascrizione e PDF",
            md_bg_color=(0.1, 0.5, 0.8, 1),
            pos_hint={'center_x': 0.5},
            on_release=self.avvia_processo
        )
        layout.add_widget(self.btn_avvia)
        
        self.add_widget(layout)
        
        # File Manager per Android
        self.file_manager = MDFileManager(
            exit_manager=self.chiudi_file_manager,
            select_path=self.seleziona_percorso
        )

    def apri_file_manager(self, *args):
        self.file_manager.show('/')

    def chiudi_file_manager(self, *args):
        self.file_manager.close()

    def seleziona_percorso(self, path):
        self.chiudi_file_manager()
        if os.path.isfile(path):
            self.file_selezionato = path
            self.lbl_file.text = os.path.basename(path)

    def aggiorna_stato(self, testo, progresso):
        self.lbl_status.text = f"Stato: {testo}"
        self.progress.value = progresso * 100

    def avvia_processo(self, *args):
        if not self.file_selezionato:
            return
        self.btn_avvia.disabled = True
        threading.Thread(target=self.esegui_elaborazione, daemon=True).start()

    def esegui_elaborazione(self):
        try:
            client = Groq(api_key=MIA_API_KEY)
            self.aggiorna_stato("Trascrizione in corso...", 0.3)
            
            with open(self.file_selezionato, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    file=(self.file_selezionato, f.read()),
                    model="whisper-large-v3",
                    prompt="Lezione universitaria in italiano",
                    response_format="verbose_json",
                    language="it"
                )
            
            testo_totale = ""
            if hasattr(transcription, "segments") and transcription.segments:
                for segment in transcription.segments:
                    txt = segment.get("text", "") if isinstance(segment, dict) else getattr(segment, "text", "")
                    testo_totale += txt.strip() + " "
            
            self.aggiorna_stato("Revisione IA...", 0.6)
            
            prompt_sistema = (
                "Sei un correttore di bozze accademico. Revisiona la trascrizione universitaria: "
                "non riassumere, non tagliare nulla, correggi solo la grammatica ed elimina i tic verbali."
            )
            
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": testo_totale}
                ],
                temperature=0.0,
            )
            testo_finale = response.choices[0].message.content.strip()
            
            self.aggiorna_stato("Generazione PDF...", 0.9)
            nome_base = os.path.splitext(os.path.basename(self.file_selezionato))[0]
            self.pdf_generato = os.path.join(os.path.dirname(self.file_selezionato), f"{nome_base}_Trascrizione.pdf")
            
            self.genera_pdf_nativo(testo_finale, self.pdf_generato)
            self.aggiorna_stato("Completato!", 1.0)
            
        except Exception as e:
            self.aggiorna_stato(f"Errore: {e}", 0)
        finally:
            self.btn_avvia.disabled = False

    def genera_pdf_nativo(self, testo, path_pdf):
        doc = SimpleDocTemplate(
            path_pdf, 
            pagesize=A4, 
            leftMargin=54, 
            rightMargin=54, 
            topMargin=54, 
            bottomMargin=54
        )
        styles = getSampleStyleSheet()

        titolo_style = ParagraphStyle(
            'Titolo',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1A2B4C"),
            spaceAfter=18
        )

        corpo_style = ParagraphStyle(
            'Corpo',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=15,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            textColor=colors.HexColor("#222222")
        )

        storia = [
            Paragraph("Trascrizione Lezione", titolo_style),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#D0D0D0"), spaceAfter=15)
        ]

        testo_pulito = (
            testo.replace("■", "-").replace("–", "-").replace("—", "-")
                 .replace("“", '"').replace("”", '"').replace("’", "'")
        )

        for p in testo_pulito.split("\n"):
            p_clean = p.strip()
            if p_clean:
                p_safe = p_clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                storia.append(Paragraph(p_safe, corpo_style))

        doc.build(storia)

class MainApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        return TrascrizioneScreen()

if __name__ == "__main__":
    MainApp().run()