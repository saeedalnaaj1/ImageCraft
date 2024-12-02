import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QScrollArea, QFileDialog,
    QSlider, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox,
    QTabWidget, QShortcut, QSpinBox, QCheckBox, QGroupBox, QGridLayout,
    QInputDialog, QSizePolicy, QAction, QWidgetAction
)
from PyQt5.QtGui import QPixmap, QImage, QKeySequence, QPainter, QPen, QPalette, QColor, QIcon, QMouseEvent
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QPoint, pyqtSlot
import cv2
import numpy as np
import qdarkstyle

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        self.start = QPoint(0, 0)
        self.pressing = False
        self.is_dark = False  # Track current theme

    def init_ui(self):
        # Set the height of the title bar
        self.setFixedHeight(40)
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b; /* Dark background by default */
            }
            QPushButton {
                border: none;
                color: white;
                background-color: transparent;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #3c3c3c;
            }
            QLabel {
                color: white;
                font-size: 14px;
                background-color: transparent; /* Ensure transparent background */
            }
        """)

        # Layout for the title bar
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        # Title Label
        self.title = QLabel("ImageCraft")
        self.title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        # Removed separate stylesheet for QLabel to inherit from parent
        layout.addWidget(self.title)

        layout.addStretch()

        # Minimize Button
        self.btn_minimize = QPushButton("-")
        self.btn_minimize.setFixedSize(30, 30)
        self.btn_minimize.clicked.connect(self.minimize_window)
        layout.addWidget(self.btn_minimize)

        # Maximize/Restore Button
        self.btn_maximize = QPushButton("□")
        self.btn_maximize.setFixedSize(30, 30)
        self.btn_maximize.clicked.connect(self.maximize_restore_window)
        layout.addWidget(self.btn_maximize)

        # Close Button
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.clicked.connect(self.close_window)
        layout.addWidget(self.btn_close)

        self.setLayout(layout)

    def minimize_window(self):
        self.parent.showMinimized()

    def maximize_restore_window(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.btn_maximize.setText("□")
        else:
            self.parent.showMaximized()
            self.btn_maximize.setText("❐")

    def close_window(self):
        self.parent.close()

    # Enable window dragging
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.pressing = True
            self.start = event.globalPos() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.pressing:
            self.parent.move(event.globalPos() - self.start)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.pressing = False

    @pyqtSlot(bool)
    def set_dark_mode(self, is_dark):
        """
        Update the title bar's stylesheet based on the theme.
        """
        self.is_dark = is_dark
        if self.is_dark:
            self.setStyleSheet("""
                QWidget {
                    background-color: #2b2b2b; /* Dark background */
                }
                QPushButton {
                    border: none;
                    color: white;
                    background-color: transparent;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #3c3c3c;
                }
                QLabel {
                    color: white;
                    font-size: 14px;
                    background-color: transparent; /* Ensure transparent background */
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: #f0f0f0; /* Light grey background */
                }
                QPushButton {
                    border: none;
                    color: black;
                    background-color: transparent;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QLabel {
                    color: black;
                    font-size: 14px;
                    background-color: transparent; /* Transparent background */
                }
            """)

class ComprehensiveImageEditor(QMainWindow):
    # Define the Dark Mode stylesheet without using the universal selector
    DARK_MODE_STYLESHEET = """
    /* Main Window */
    QMainWindow {
        background-color: #2b2b2b;
        color: #ffffff;
    }

    /* Menu Bar */
    QMenuBar {
        background-color: #2b2b2b;
        color: #ffffff;
    }
    QMenuBar::item:selected {
        background-color: #3c3c3c;
    }

    /* Menus */
    QMenu {
        background-color: #2b2b2b;
        color: #ffffff;
    }
    QMenu::item:selected {
        background-color: #3c3c3c;
    }

    /* Push Buttons */
    QPushButton {
        background-color: #3c3c3c;
        color: #ffffff;
        border: 1px solid #555555;
        padding: 3px 6px;  /* Reduced padding */
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #5c5c5c;
    }

    /* Sliders */
    QSlider::groove:horizontal {
        border: 1px solid #bbb;
        background: #3c3c3c;
        height: 6px;  /* Reduced height */
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #5c5c5c;
        border: 1px solid #5c5c5c;
        width: 12px;  /* Reduced width */
        margin: -3px 0;  /* Adjusted margin */
        border-radius: 6px;  /* Adjusted radius */
    }

    /* Checkboxes */
    QCheckBox {
        spacing: 4px;  /* Reduced spacing */
    }

    /* Spin Boxes */
    QSpinBox {
        background-color: #3c3c3c;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 1px 3px;  /* Reduced padding */
        color: #ffffff;
    }

    /* Labels */
    QLabel {
        color: #ffffff;
    }

    /* Tab Widget Pane */
    QTabWidget::pane {
        border: 1px solid #555555;
    }

    /* Tab Bar */
    QTabBar::tab {
        background-color: #3c3c3c;
        color: #ffffff;
        padding: 8px;  /* Reduced padding */
        margin: 1px;  /* Reduced margin */
    }
    QTabBar::tab:selected {
        background-color: #5c5c5c;
    }

    /* Group Boxes */
    QGroupBox {
        border: 1px solid #555555;
        border-radius: 5px;
        margin-top: 0; /* Remove margin-top */
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 3px;
    }

    /* Scroll Areas */
    QScrollArea {
        background-color: #2b2b2b;
    }

    /* Preview Label Specific Styling */
    QLabel#PreviewLabel {
        background-color: #1e1e1e;
        border: 1px solid #555555;
        color: #ffffff;
        font-size: 14px;
        text-align: center;
    }
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle('ImageCraft')
        self.setGeometry(100, 100, 800, 600)  # Initial window size
        self.setMinimumSize(800, 600)  # Prevent window from being too small
        self.setWindowFlags(Qt.FramelessWindowHint)  # Remove OS title bar

        # Main widget and layout
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

        # Add custom title bar
        self.title_bar = CustomTitleBar(self)
        self.main_layout.addWidget(self.title_bar)

        # Initialize tabs
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # Image Transformation tab
        self.transformation_tab = ImageTransformationTab()
        self.tabs.addTab(self.transformation_tab, "Image Transformation")

        # HCT and Auto Labeling tab
        self.hct_tab = HCTAutoLabelTab()
        self.tabs.addTab(self.hct_tab, "HCT and Auto Labeling")

        # Image Augmentation tab
        self.augmentation_tab = ImageAugmentationTab()
        self.tabs.addTab(self.augmentation_tab, "Image Augmentation")

        # Initialize Menu
        self.init_menu()

        # Initialize Keyboard Shortcuts
        self.init_shortcuts()

        # Initialize Status Bar
        self.statusBar().showMessage("Ready")

        # Set focus to the main window
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        # **Set initial theme to light mode**
        self.title_bar.set_dark_mode(False)

        logging.debug("ComprehensiveImageEditor initialized successfully.")


    def init_menu(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu('File')

        load_image_action = QAction('Load Image', self)
        load_image_action.triggered.connect(self.load_image)
        file_menu.addAction(load_image_action)

        load_folder_action = QAction('Load Folder', self)
        load_folder_action.triggered.connect(self.load_folder)
        file_menu.addAction(load_folder_action)

        save_image_action = QAction('Save Image', self)
        save_image_action.triggered.connect(self.save_image)
        file_menu.addAction(save_image_action)

        save_all_action = QAction('Save All', self)
        save_all_action.triggered.connect(self.save_all)
        file_menu.addAction(save_all_action)

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Theme Menu
        theme_menu = menu_bar.addMenu('Theme')

        dark_mode_action = QAction('Dark Mode', self, checkable=True)
        dark_mode_action.setStatusTip('Toggle Dark Mode')
        dark_mode_action.setChecked(False)  # Ensure it's unchecked by default
        dark_mode_action.toggled.connect(self.toggle_dark_mode)  # Connect to toggled(bool)
        theme_menu.addAction(dark_mode_action)

        # Help Menu
        help_menu = menu_bar.addMenu('Help')
        help_action = QAction('Help', self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

        logging.debug("Menu initialized successfully.")

    def init_shortcuts(self):

        # 1. Load Image: Ctrl+O
        load_image_action = QAction("Load Image", self)
        load_image_action.setShortcut(QKeySequence("Ctrl+O"))
        load_image_action.triggered.connect(self.load_image)
        load_image_action.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(load_image_action)

        # 2. Load Folder: Ctrl+Shift+O
        load_folder_action = QAction("Load Folder", self)
        load_folder_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        load_folder_action.triggered.connect(self.load_folder)  # Connect to load_folder method
        load_folder_action.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(load_folder_action)

        # 3. Save Image: Ctrl+S
        save_image_action = QAction("Save Image", self)
        save_image_action.setShortcut(QKeySequence("Ctrl+S"))
        save_image_action.triggered.connect(self.save_image)
        save_image_action.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(save_image_action)

        # 4. Save All: Ctrl+Shift+S
        save_all_action = QAction("Save All", self)
        save_all_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_all_action.triggered.connect(self.save_all)
        save_all_action.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(save_all_action)

        # 5. Quit Application: Ctrl+Q
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        quit_action.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(quit_action)

        # 6. Zoom In: Ctrl++
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut(QKeySequence("Ctrl++"))
        zoom_in_action.triggered.connect(self.zoom_in)
        zoom_in_action.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(zoom_in_action)

        # 7. Zoom Out: Ctrl+-
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
        zoom_out_action.triggered.connect(self.zoom_out)
        zoom_out_action.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(zoom_out_action)

        # 8. Previous Image: A
        prev_image_action = QAction("Previous Image", self)
        prev_image_action.setShortcut(QKeySequence("A"))
        prev_image_action.triggered.connect(self.previous_image)
        prev_image_action.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(prev_image_action)

        # 9. Next Image: D
        next_image_action = QAction("Next Image", self)
        next_image_action.setShortcut(QKeySequence("D"))
        next_image_action.triggered.connect(self.next_image)
        next_image_action.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(next_image_action)

        logging.debug("Keyboard shortcuts initialized successfully.")

    def toggle_dark_mode(self, checked):
        try:
            if checked:
                QApplication.instance().setStyleSheet(self.DARK_MODE_STYLESHEET)
                self.statusBar().showMessage("Dark Mode Enabled", 2000)
                logging.info("Dark Mode Enabled")
            else:
                QApplication.instance().setStyleSheet("")  # Revert to default light mode
                self.statusBar().showMessage("Dark Mode Disabled", 2000)
                logging.info("Dark Mode Disabled")

            # **Begin: Option 1 Implementation**
            # Append styles for QMessageBox to ensure white background and black text
            QMessageBox_stylesheet = """
            QMessageBox {
                background-color: white;
                color: black;
            }
            QMessageBox QLabel {
                color: black;
            }
            QMessageBox QPushButton {
                background-color: #3c3c3c;
                color: #ffffff;
            }
            """
            # Apply the QMessageBox styles on top of the existing stylesheet
            QApplication.instance().setStyleSheet(QApplication.instance().styleSheet() + QMessageBox_stylesheet)
            logging.debug("QMessageBox styles applied to maintain readability.")

            # **End: Option 1 Implementation**

            # Invalidate and activate each tab's layout if it exists
            for index in range(self.tabs.count()):
                tab = self.tabs.widget(index)
                if tab.layout() is not None:
                    tab.layout().invalidate()
                    tab.layout().activate()
                else:
                    logging.warning(f"Tab at index {index} does not have a layout.")

            # Refresh the UI to apply changes
            self.repaint()

            # Log widget sizes for debugging
            self.log_widget_sizes()

            # **Update the title bar's style**
            self.title_bar.set_dark_mode(checked)

            logging.debug("Dark mode toggled successfully.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to toggle dark mode: {e}")
            logging.error(f"Failed to toggle dark mode: {e}")

    def log_widget_sizes(self):
        logging.debug(f"Main Window Size: {self.size()}")
        logging.debug(f"Tabs Size: {self.tabs.size()}")
        for index in range(self.tabs.count()):
            tab = self.tabs.widget(index)
            logging.debug(f"Tab {index} Size: {tab.size()}")
            for child in tab.findChildren(QWidget):
                logging.debug(f"  Widget '{child.objectName()}' Size: {child.size()}")

    def get_active_tab(self):
        """Returns the currently active tab widget."""
        return self.tabs.currentWidget()

    def load_image(self):
        # Delegate load image functionality to the active tab
        current_tab = self.get_active_tab()
        if hasattr(current_tab, 'load_image'):
            current_tab.load_image()
            self.statusBar().showMessage("Image loaded.", 2000)
        else:
            QMessageBox.warning(self, "Action Not Available", "Load Image action is not available in the current tab.")

    def load_folder(self):
        # Delegate load folder functionality to the active tab
        current_tab = self.get_active_tab()
        if hasattr(current_tab, 'load_folder'):
            current_tab.load_folder()
            self.statusBar().showMessage("Folder loaded.", 2000)
        else:
            QMessageBox.warning(self, "Action Not Available", "Load Folder action is not available in the current tab.")

    def save_image(self):
        # Delegate save image functionality to the active tab
        current_tab = self.get_active_tab()
        if hasattr(current_tab, 'save_image'):
            current_tab.save_image()
            self.statusBar().showMessage("Image saved.", 2000)
        else:
            QMessageBox.warning(self, "Action Not Available", "Save Image action is not available in the current tab.")

    def save_all(self):
        # Delegate save all functionality to the active tab
        current_tab = self.get_active_tab()
        if hasattr(current_tab, 'save_all'):
            current_tab.save_all()
            self.statusBar().showMessage("All images saved.", 2000)
        else:
            QMessageBox.warning(self, "Action Not Available", "Save All action is not available in the current tab.")

    def next_image(self):
        # Delegate next image action to the active tab
        current_tab = self.get_active_tab()
        if hasattr(current_tab, 'next_image'):
            print("Shortcut: Next Image triggered")
            current_tab.next_image()
            self.statusBar().showMessage("Next Image triggered via shortcut.", 2000)
        else:
            QMessageBox.warning(self, "Action Not Available", "Next Image action is not available in the current tab.")

    def previous_image(self):
        # Delegate previous image action to the active tab
        current_tab = self.get_active_tab()
        if hasattr(current_tab, 'previous_image'):
            print("Shortcut: Previous Image triggered")
            current_tab.previous_image()
            self.statusBar().showMessage("Previous Image triggered via shortcut.", 2000)
        else:
            QMessageBox.warning(self, "Action Not Available", "Previous Image action is not available in the current tab.")

    def zoom_in(self):
        # Delegate zoom in action to the active tab
        current_tab = self.get_active_tab()
        if hasattr(current_tab, 'zoom_in'):
            print("Shortcut: Zoom In triggered")
            current_tab.zoom_in()
            self.statusBar().showMessage("Zoom In triggered via shortcut.", 2000)
        else:
            QMessageBox.warning(self, "Action Not Available", "Zoom In action is not available in the current tab.")

    def zoom_out(self):
        # Delegate zoom out action to the active tab
        current_tab = self.get_active_tab()
        if hasattr(current_tab, 'zoom_out'):
            print("Shortcut: Zoom Out triggered")
            current_tab.zoom_out()
            self.statusBar().showMessage("Zoom Out triggered via shortcut.", 2000)
        else:
            QMessageBox.warning(self, "Action Not Available", "Zoom Out action is not available in the current tab.")

    def show_help(self):
        # Show help information
        help_text = """
        
        Welcome To ImageCraft ! :
        
        This is a comprehensive image editor that combines:
        - Image Transformation (Perspective, Translation, Cropping) etc...
        - Hough Circle Transform with Auto Labeling
        - Image Augmentation ( Based On YOLO Augmentations )

        Use the tabs to switch between functionalities.
        
        A Dark Mode Is Available For Your Convenience , Activate It In "Theme" .

        Keyboard Shortcuts:
        - Next Image: D
        - Previous Image: A
        - Zoom In: Ctrl + +
        - Zoom Out: Ctrl + -
        - Load Image: Ctrl+O
        - Load Folder: Ctrl+Shift+O
        - Save Image: Ctrl+S
        - Save All: Ctrl+Shift+S
        - Quit Application: Ctrl+Q
        
        Important Warning : If you save your work in the same folder each time, 
        you risk overwriting previous files. To prevent this, 
        always create a separate folder for each image set, 
        especially when using different types of augmentation. 
        This will help you keep your work organized and avoid any loss of data.
        
        
        Tool Developer : Saeed Sameeh Abualnaaj - Junior Computer Vision Engineer 
        """
        QMessageBox.information(self, "Help", help_text)



class ImageTransformationTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)

        # Initialize variables
        self.img = None
        self.transformed_img = None
        self.scale_factor = 1.0
        self.lines = []
        self.file_paths = []
        self.current_index = -1

        # Setup UI
        self.init_ui()

    def init_ui(self):
        # Main layout
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # Image display
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.image_label = QLabel("Load an image to begin.")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("QLabel { background-color : lightgray; }")
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll_area.setWidget(self.image_label)
        main_layout.addWidget(self.scroll_area, 3)

        # Controls layout
        controls_widget = QWidget()
        controls_widget.setMaximumWidth(300)
        controls_layout = QVBoxLayout()
        controls_layout.setContentsMargins(5, 5, 5, 5)
        controls_widget.setLayout(controls_layout)
        controls_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        main_layout.addWidget(controls_widget, 1)

        # Buttons
        buttons_group = QGroupBox("Controls")
        buttons_layout = QGridLayout()
        buttons_layout.setSpacing(5)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_group.setLayout(buttons_layout)
        controls_layout.addWidget(buttons_group)

        buttons = [
            ("Load Image", self.load_image),
            ("Load Folder", self.load_folder),
            ("Save Image", self.save_image),
            ("Save All", self.save_all),
            ("Apply", self.apply_transformation),
            ("Apply to All", self.apply_transformation_to_all),
            ("Reset Image", self.reset_image),
            ("Reset All", self.reset_all),
            ("Zoom In", self.zoom_in),
            ("Zoom Out", self.zoom_out),
            ("Draw Lines", self.draw_lines),
            ("Remove Lines", self.remove_lines),
            ("Previous (A)", self.previous_image),
            ("Next (D)", self.next_image)
        ]

        columns = 2
        for i, (text, method) in enumerate(buttons):
            button = QPushButton(text)
            button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            button.setMaximumWidth(140)
            button.clicked.connect(method)
            row = i // columns
            col = i % columns
            buttons_layout.addWidget(button, row, col)

        # Image info label
        self.image_info_label = QLabel("No images loaded.")
        self.image_info_label.setAlignment(Qt.AlignCenter)
        controls_layout.addWidget(self.image_info_label)

        # Sliders and Controls
        self.init_sliders(controls_layout)

    def init_sliders(self, controls_layout):
        # Helper function to create sliders
        def create_slider(label_text, min_val, max_val, default, tick_interval):
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)
            label = QLabel(label_text)
            label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(min_val)
            slider.setMaximum(max_val)
            slider.setValue(default)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(tick_interval)
            slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            value_label = QLabel(str(default))
            value_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            slider.valueChanged.connect(lambda value, lbl=value_label: lbl.setText(str(value)))
            slider.valueChanged.connect(self.update_transformation)
            layout.addWidget(label)
            layout.addWidget(slider)
            layout.addWidget(value_label)
            return slider, value_label, layout

        # 1. Perspective Controls
        perspective_group = QGroupBox("Perspective Controls")
        perspective_layout = QVBoxLayout()
        perspective_layout.setContentsMargins(5, 5, 5, 5)
        perspective_layout.setSpacing(5)
        perspective_group.setLayout(perspective_layout)
        controls_layout.addWidget(perspective_group)

        # Corner Sliders
        self.corners = []
        corner_labels = ["Top-Left (X)", "Top-Left (Y)",
                         "Top-Right (X)", "Top-Right (Y)",
                         "Bottom-Right (X)", "Bottom-Right (Y)",
                         "Bottom-Left (X)", "Bottom-Left (Y)"]
        corner_default_values = [0, 0, 1920, 0, 1920, 1080, 0, 1080]

        for i, label in enumerate(corner_labels):
            # Adjust max_val based on whether it's X or Y
            max_val = 1920 if 'X' in label else 1080
            slider, value_label, slider_layout = create_slider(
                label_text=label,
                min_val=0,
                max_val=max_val,
                default=corner_default_values[i],
                tick_interval=100
            )
            perspective_layout.addLayout(slider_layout)
            self.corners.append(slider)

        # 2. Transformation Controls
        transformation_group = QGroupBox("Transformation Controls")
        transformation_layout = QVBoxLayout()
        transformation_layout.setContentsMargins(5, 5, 5, 5)
        transformation_layout.setSpacing(5)
        transformation_group.setLayout(transformation_layout)
        controls_layout.addWidget(transformation_group)

        # X Translation
        self.x_translation_slider, self.x_translation_value_label, x_trans_layout = create_slider(
            label_text="X Translation:",
            min_val=-500,
            max_val=500,
            default=0,
            tick_interval=100
        )
        transformation_layout.addLayout(x_trans_layout)

        # Y Translation
        self.y_translation_slider, self.y_translation_value_label, y_trans_layout = create_slider(
            label_text="Y Translation:",
            min_val=-500,
            max_val=500,
            default=0,
            tick_interval=100
        )
        transformation_layout.addLayout(y_trans_layout)

        # Scale
        self.scale_slider, self.scale_value_label, scale_layout = create_slider(
            label_text="Scale (%):",
            min_val=10,
            max_val=500,
            default=100,
            tick_interval=10
        )
        transformation_layout.addLayout(scale_layout)

        # Rotation
        self.rotation_slider, self.rotation_value_label, rotation_layout = create_slider(
            label_text="Rotation (°):",
            min_val=-360,
            max_val=360,
            default=0,
            tick_interval=30
        )
        transformation_layout.addLayout(rotation_layout)

        # Crop X
        self.crop_x_slider, self.crop_x_value_label, crop_x_layout = create_slider(
            label_text="Crop X:",
            min_val=0,
            max_val=1920,
            default=0,
            tick_interval=100
        )
        transformation_layout.addLayout(crop_x_layout)

        # Crop Y
        self.crop_y_slider, self.crop_y_value_label, crop_y_layout = create_slider(
            label_text="Crop Y:",
            min_val=0,
            max_val=1080,
            default=0,
            tick_interval=100
        )
        transformation_layout.addLayout(crop_y_layout)

        # Crop Width
        self.crop_width_slider, self.crop_width_value_label, crop_w_layout = create_slider(
            label_text="Crop Width:",
            min_val=1,
            max_val=1920,
            default=1920,
            tick_interval=100
        )
        transformation_layout.addLayout(crop_w_layout)

        # Crop Height
        self.crop_height_slider, self.crop_height_value_label, crop_h_layout = create_slider(
            label_text="Crop Height:",
            min_val=1,
            max_val=1080,
            default=1080,
            tick_interval=100
        )
        transformation_layout.addLayout(crop_h_layout)

    def setup_shortcuts(self):
        # Previous Image Shortcut (A key)
        self.shortcut_prev = QShortcut(QKeySequence('A'), self)
        self.shortcut_prev.setContext(Qt.ApplicationShortcut)
        self.shortcut_prev.activated.connect(self.previous_image)

        # Next Image Shortcut (D key)
        self.shortcut_next = QShortcut(QKeySequence('D'), self)
        self.shortcut_next.setContext(Qt.ApplicationShortcut)
        self.shortcut_next.activated.connect(self.next_image)

        # Zoom In: Ctrl + +
        self.shortcut_zoom_in = QShortcut(QKeySequence('Ctrl++'), self)
        self.shortcut_zoom_in.setContext(Qt.ApplicationShortcut)
        self.shortcut_zoom_in.activated.connect(self.zoom_in)

        # Zoom Out: Ctrl + -
        self.shortcut_zoom_out = QShortcut(QKeySequence('Ctrl+-'), self)
        self.shortcut_zoom_out.setContext(Qt.ApplicationShortcut)
        self.shortcut_zoom_out.activated.connect(self.zoom_out)

    def load_image(self):
        # Implement load image functionality
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Image files (*.jpg *.jpeg *.png)"
        )
        if file_path:
            self.file_paths = [file_path]
            self.current_index = 0
            self.transformed_images = {}  # Reset transformed images
            self.load_current_image()

    def load_folder(self):
        # Implement load folder functionality
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", ""
        )
        if folder_path:
            supported_formats = (".jpg", ".jpeg", ".png")
            self.file_paths = [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if f.lower().endswith(supported_formats)
            ]
            if not self.file_paths:
                QMessageBox.warning(self, "No Images", "No images found in the selected folder.")
                return
            self.current_index = 0
            self.transformed_images = {}  # Reset transformed images
            self.load_current_image()

    def load_current_image(self):
        if 0 <= self.current_index < len(self.file_paths):
            file_path = self.file_paths[self.current_index]
            if file_path in self.transformed_images:
                # Use the transformed image if available
                self.transformed_img = self.transformed_images[file_path]
                try:
                    # Display the transformed image directly
                    self.update_display_image(self.transformed_img)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to display transformed image: {e}")
                    self.image_label.setText("Failed to display image.")
                    self.image_info_label.setText("No images loaded.")
            else:
                try:
                    self.img = cv2.imread(file_path)
                    if self.img is None:
                        raise ValueError("Image data is None. Possibly unsupported image format or corrupted file.")
                    self.img = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
                    self.transformed_img = None
                    # Reset transformation-related variables
                    self.lines = []
                    self.reset_sliders()
                    self.update_display_image(self.img)
                    self.update_image_info()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load image: {file_path}\n{e}")
                    self.img = None
                    self.transformed_img = None
                    self.image_label.setText("Failed to load image.")
                    self.image_info_label.setText("No images loaded.")
        else:
            QMessageBox.warning(self, "Index Error", "Image index out of range.")

    def update_display_image(self, img):
        if img is None:
            self.image_label.setText("No image to display.")
            return
        img = np.require(img, np.uint8, 'C')
        height, width, channel = img.shape
        bytes_per_line = 3 * width
        try:
            q_img = QImage(img.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()
            if q_img.isNull():
                raise ValueError("QImage is null. Possibly unsupported image format.")
            pixmap = QPixmap.fromImage(q_img)
        except Exception as e:
            QMessageBox.critical(self, "Image Error", f"Failed to convert image for display: {e}")
            self.image_label.setText("Failed to display image.")
            return

        scaled_pixmap = pixmap.scaled(
            int(pixmap.width() * self.scale_factor),
            int(pixmap.height() * self.scale_factor),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        if self.lines:
            painter = QPainter(scaled_pixmap)
            pen = QPen(Qt.black, 3)
            painter.setPen(pen)
            for line_y in self.lines:
                scaled_y = int(line_y * self.scale_factor)
                if 0 <= scaled_y <= scaled_pixmap.height():
                    painter.drawLine(0, scaled_y, scaled_pixmap.width(), scaled_y)
            painter.end()

        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.adjustSize()

    def apply_transformation(self):
        if self.img is None:
            QMessageBox.warning(self, "No Image", "No image loaded to apply transformations.")
            return

        try:
            # Apply transformations
            transformed_img = self.apply_transformations(self.img.copy())
            self.transformed_img = transformed_img
            self.transformed_images[self.file_paths[self.current_index]] = transformed_img
            self.update_display_image(self.transformed_img)
        except Exception as e:
            QMessageBox.critical(self, "Transformation Error", f"An error occurred during transformation:\n{e}")

    def apply_transformation_to_all(self):
        if len(self.file_paths) == 0:
            QMessageBox.warning(self, "No Images", "No images loaded to apply transformations.")
            return

        self.transformed_images = {}  # Reset transformed images

        for idx, file_path in enumerate(self.file_paths):
            try:
                img = cv2.imread(file_path)
                if img is None:
                    raise ValueError("Image data is None. Possibly unsupported image format or corrupted file.")
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                # Apply transformations on a copy to prevent altering the original image
                transformed_img = self.apply_transformations(img.copy())

                # Store the transformed image
                self.transformed_images[file_path] = transformed_img

            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to process image {os.path.basename(file_path)}: {e}")

        QMessageBox.information(self, "Transformation Applied", "Transformations have been applied to all images.")

        # Update the current image display if necessary
        self.load_current_image()

    def apply_transformations(self, img):
        src_points = np.array([
            [self.corners[0].value(), self.corners[1].value()],
            [self.corners[2].value(), self.corners[3].value()],
            [self.corners[4].value(), self.corners[5].value()],
            [self.corners[6].value(), self.corners[7].value()]
        ], dtype="float32")

        if not self.validate_points(src_points):
            raise ValueError("Invalid perspective points.")

        # Apply perspective transformation
        transformed_img = self.perspective_transform(img, src_points)

        # Apply translation
        M_translate = np.float32([[1, 0, self.x_translation_slider.value()],
                                  [0, 1, self.y_translation_slider.value()]])
        transformed_img = cv2.warpAffine(transformed_img, M_translate,
                                         (transformed_img.shape[1], transformed_img.shape[0]))

        # Apply rotation and scaling
        h, w = transformed_img.shape[:2]
        center = (w // 2, h // 2)

        scale = self.scale_slider.value() / 100  # Convert to float
        rotation = self.rotation_slider.value()

        M_rotate = cv2.getRotationMatrix2D(center, rotation, scale)
        transformed_img = cv2.warpAffine(transformed_img, M_rotate, (w, h))

        # Apply cropping
        crop_x = int(self.crop_x_slider.value())
        crop_y = int(self.crop_y_slider.value())
        crop_w = int(self.crop_width_slider.value())
        crop_h = int(self.crop_height_slider.value())

        # Ensure crop dimensions are within the bounds of the image
        crop_w = min(crop_w, transformed_img.shape[1] - crop_x)
        crop_h = min(crop_h, transformed_img.shape[0] - crop_y)

        if crop_x < 0 or crop_y < 0 or crop_w <= 0 or crop_h <= 0:
            raise ValueError("Invalid crop dimensions.")

        transformed_img = transformed_img[crop_y:crop_y + crop_h, crop_x:crop_x + crop_w]

        return transformed_img

    def validate_points(self, points):
        try:
            if points.shape != (4, 2):
                return False
            if len(np.unique(points, axis=0)) != 4:
                return False
            hull = cv2.convexHull(points)
            return len(hull) == 4
        except:
            return False

    def perspective_transform(self, img, src_points):
        h, w = img.shape[:2]
        dst_points = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype="float32")
        try:
            M = cv2.getPerspectiveTransform(src_points, dst_points)
            transformed_img = cv2.warpPerspective(img, M, (w, h))
            return transformed_img
        except cv2.error as e:
            raise ValueError(f"Perspective transformation failed: {e}")

    def update_transformation(self):
        pass  # Optional: Implement real-time transformation updates here

    def reset_sliders(self):
        # Reset sliders to their default values and adjust maximums based on image dimensions
        img_to_use = self.transformed_img if self.transformed_img is not None else self.img
        if img_to_use is not None:
            img_height, img_width = img_to_use.shape[:2]
        else:
            img_height, img_width = 1080, 1920  # default

        # Update corner sliders
        for i, slider in enumerate(self.corners):
            if i % 2 == 0:  # X sliders
                slider.setMaximum(img_width)
                if i in [0, 6]:  # Top-Left X and Bottom-Left X
                    slider.setValue(0)
                else:  # Top-Right X and Bottom-Right X
                    slider.setValue(img_width)
            else:  # Y sliders
                slider.setMaximum(img_height)
                if i in [1, 3]:  # Top-Left Y and Top-Right Y
                    slider.setValue(0)
                else:  # Bottom-Right Y and Bottom-Left Y
                    slider.setValue(img_height)

        # Update translation sliders
        self.x_translation_slider.setMinimum(-img_width // 2)
        self.x_translation_slider.setMaximum(img_width // 2)
        self.x_translation_slider.setValue(0)

        self.y_translation_slider.setMinimum(-img_height // 2)
        self.y_translation_slider.setMaximum(img_height // 2)
        self.y_translation_slider.setValue(0)

        # Update scale slider
        self.scale_slider.setValue(100)  # Default scale is 100%

        # Update rotation slider
        self.rotation_slider.setValue(0)

        # Update crop sliders
        self.crop_x_slider.setMaximum(img_width)
        self.crop_x_slider.setValue(0)

        self.crop_y_slider.setMaximum(img_height)
        self.crop_y_slider.setValue(0)

        self.crop_width_slider.setMaximum(img_width)
        self.crop_width_slider.setValue(img_width)

        self.crop_height_slider.setMaximum(img_height)
        self.crop_height_slider.setValue(img_height)

    def save_image(self):
        if self.transformed_img is None:
            QMessageBox.critical(self, "Error", "No transformed image to save!")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "PNG files (*.png);;JPEG files (*.jpg *.jpeg)"
        )
        if save_path:
            try:
                transformed_img_bgr = cv2.cvtColor(self.transformed_img, cv2.COLOR_RGB2BGR)
                cv2.imwrite(save_path, transformed_img_bgr)
                QMessageBox.information(self, "Saved", f"Image saved to {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save image: {e}")

    def save_all(self):
        if not self.file_paths:
            QMessageBox.warning(self, "No Images", "No images loaded to save.")
            return

        if not self.transformed_images:
            QMessageBox.warning(self, "No Transformations", "No transformations applied to save.")
            return

        save_folder = QFileDialog.getExistingDirectory(
            self, "Select Save Folder", ""
        )
        if not save_folder:
            return

        for file_path, transformed_img in self.transformed_images.items():
            try:
                save_path = os.path.join(save_folder, os.path.basename(file_path))
                transformed_img_bgr = cv2.cvtColor(transformed_img, cv2.COLOR_RGB2BGR)
                cv2.imwrite(save_path, transformed_img_bgr)
            except Exception as e:
                QMessageBox.warning(self, "Save Error", f"Failed to save image {file_path}: {e}")
                continue

        QMessageBox.information(self, "Save All", "All transformed images have been saved successfully.")

    def update_image_info(self):
        if self.file_paths:
            self.image_info_label.setText(
                f"Image {self.current_index + 1} of {len(self.file_paths)}"
            )
        else:
            self.image_info_label.setText("No images loaded.")

    def reset_image(self):
        if self.file_paths and self.current_index >= 0:
            # Remove any transformed image for current image
            file_path = self.file_paths[self.current_index]
            if file_path in self.transformed_images:
                del self.transformed_images[file_path]
            self.transformed_img = None
            self.lines = []
            self.reset_sliders()
            self.load_current_image()
        else:
            QMessageBox.warning(self, "No Image", "No image loaded to reset.")

    def reset_all(self):
        if not self.file_paths:
            return
        self.transformed_images = {}
        self.transformed_img = None
        self.lines = []
        self.reset_sliders()
        self.load_current_image()

    def draw_lines(self):
        if self.img is None and self.transformed_img is None:
            QMessageBox.critical(self, "Error", "No image loaded!")
            return

        img_to_draw = self.transformed_img if self.transformed_img is not None else self.img
        h, w = img_to_draw.shape[:2]

        line_y, ok = QInputDialog.getInt(
            self, "Draw Line", f"Enter the Y position for the line (0 to {h}):", 0, 0, h, 1
        )
        if ok:
            if 0 <= line_y <= h:
                self.lines.append(line_y)
                self.update_display_image(img_to_draw)
            else:
                QMessageBox.warning(self, "Invalid Input", f"Y position must be between 0 and {h}.")

    def remove_lines(self):
        self.lines.clear()
        self.update_display_image(self.img if self.transformed_img is None else self.transformed_img)

    def zoom_in(self):
        if self.scale_factor < 5.0:
            self.scale_factor *= 1.1
            self.update_display_image(self.transformed_img or self.img)

    def zoom_out(self):
        if self.scale_factor > 0.1:
            self.scale_factor /= 1.1
            self.update_display_image(self.transformed_img or self.img)

    def next_image(self):
        if not self.file_paths:
            QMessageBox.warning(self, "No Images", "No images loaded.")
            return

        if self.current_index < len(self.file_paths) - 1:
            self.current_index += 1
            self.load_current_image()
        else:
            QMessageBox.information(self, "End", "This is the last image.")

    def previous_image(self):
        if not self.file_paths:
            QMessageBox.warning(self, "No Images", "No images loaded.")
            return

        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_image()
        else:
            QMessageBox.information(self, "Start", "This is the first image.")



class HCTAutoLabelTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)

        # Initialize variables
        self.image = None
        self.original_image = None
        self.processed_images = {}
        self.image_dir = ''
        self.current_image_path = ''
        self.zoom_level = 1.0
        self.image_list = []
        self.current_image_index = 0
        self.bounding_boxes = {}
        self.offset = 10

        # Setup UI
        self.init_ui()

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFocusPolicy(Qt.NoFocus)  # Prevent label from stealing focus
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.image_label)
        main_layout.addWidget(self.scroll_area, stretch=5)

        # Buttons and sliders
        self.create_buttons(main_layout)
        self.create_sliders(main_layout)

        # Setup keyboard shortcuts
        #self.setup_shortcuts()

        # Set focus policy and focus
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

    """
    def setup_shortcuts(self):
        # Previous Image Shortcut (A key)
        self.shortcut_prev = QShortcut(QKeySequence('A'), self)
        self.shortcut_prev.setContext(Qt.ApplicationShortcut)
        self.shortcut_prev.activated.connect(self.previous_image)

        # Next Image Shortcut (D key)
        self.shortcut_next = QShortcut(QKeySequence('D'), self)
        self.shortcut_next.setContext(Qt.ApplicationShortcut)
        self.shortcut_next.activated.connect(self.next_image)

        # Zoom In: Ctrl + +
        self.shortcut_zoom_in = QShortcut(QKeySequence('Ctrl++'), self)
        self.shortcut_zoom_in.setContext(Qt.ApplicationShortcut)
        self.shortcut_zoom_in.activated.connect(self.zoom_in)

        # Zoom Out: Ctrl + -
        self.shortcut_zoom_out = QShortcut(QKeySequence('Ctrl+-'), self)
        self.shortcut_zoom_out.setContext(Qt.ApplicationShortcut)
        self.shortcut_zoom_out.activated.connect(self.zoom_out)
    """

    def create_buttons(self, layout):
        # Buttons layout with two rows using QHBoxLayout
        buttons_layout = QVBoxLayout()

        # First row of buttons
        button_row1 = QHBoxLayout()
        button_row1.setSpacing(5)

        buttons1 = [
            ('Zoom In', self.zoom_in),
            ('Zoom Out', self.zoom_out),
            ('Load Image', self.load_image),
            ('Save Image', self.save_image),
            ('Reset Image', self.reset_image),
            ('Reset All', self.reset_all)
        ]

        for text, method in buttons1:
            button = QPushButton(text)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(method)
            button_row1.addWidget(button)

        buttons_layout.addLayout(button_row1)

        # Second row of buttons
        button_row2 = QHBoxLayout()
        button_row2.setSpacing(5)

        buttons2 = [
            ('Apply HCT', self.apply_hct),
            ('Apply HCT To All', self.apply_hct_all),
            ('Apply HCT with BBoxes', self.apply_hct_with_bboxes),
            ('Apply HCT with BBoxes To All', self.apply_hct_with_bboxes_all),
            ('Save All', self.save_all),
            ('Save Annotations', self.save_annotations),
            ('Save All Annotations', self.save_all_annotations),
            ('Reset Sliders', self.reset_sliders),
            ('Load/Open Directory', self.load_directory),
            ('Previous', self.previous_image),
            ('Next', self.next_image),
            ('?', self.show_help)
        ]

        for text, method in buttons2:
            button = QPushButton(text)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(method)
            button_row2.addWidget(button)

        buttons_layout.addLayout(button_row2)

        layout.addLayout(buttons_layout)

    def create_sliders(self, layout):
        # Sliders layout
        slider_layout = QVBoxLayout()

        # Adjust dp_slider for floating-point values
        sliders = [
            # Label, Attribute name, Default, Min, Max, Step, Mapping Function
            ('dp - Inverse ratio of resolution', 'dp', 100, 10, 1000, 10, lambda x: x / 100.0),
            ('minDist - Min distance between circles', 'minDist', 20, 1, 500, 10, lambda x: x),
            ('param1 - Upper threshold for Canny', 'param1', 50, 1, 300, 10, lambda x: x),
            ('param2 - Threshold for center detection', 'param2', 30, 1, 100, 5, lambda x: x),
            ('minRadius - Minimum circle radius', 'minRadius', 0, 0, 100, 5, lambda x: x),
            ('maxRadius - Maximum circle radius', 'maxRadius', 0, 0, 200, 10, lambda x: x)
        ]

        for i, (label_text, attr, default, min_val, max_val, tick_interval, mapping) in enumerate(sliders):
            slider, value_label, slider_layout_inner = self.create_slider(label_text, min_val, max_val, default, tick_interval, mapping)
            slider_layout.addLayout(slider_layout_inner)
            setattr(self, f"{attr}_slider", slider)
            setattr(self, f"{attr}_value_label", value_label)

        # Class number selector
        class_layout = QHBoxLayout()
        class_label = QLabel('Class Number')
        class_label.setFixedWidth(250)
        class_layout.addWidget(class_label)
        self.class_number_selector = QSpinBox()
        self.class_number_selector.setMinimum(0)
        self.class_number_selector.setMaximum(99)
        self.class_number_selector.setValue(0)
        class_layout.addWidget(self.class_number_selector)
        class_value_label = QLabel(str(self.class_number_selector.value()))
        class_value_label.setFixedWidth(50)
        class_layout.addWidget(class_value_label)
        self.class_number_selector.valueChanged.connect(lambda value: class_value_label.setText(str(value)))
        slider_layout.addLayout(class_layout)

        # Offset input for bounding boxes
        offset_layout = QHBoxLayout()
        offset_label = QLabel('Bounding Box Offset (pixels)')
        offset_label.setFixedWidth(250)
        offset_layout.addWidget(offset_label)
        self.offset_input = QSpinBox()
        self.offset_input.setMinimum(0)
        self.offset_input.setMaximum(100)
        self.offset_input.setValue(self.offset)
        offset_layout.addWidget(self.offset_input)
        offset_value_label = QLabel(str(self.offset_input.value()))
        offset_value_label.setFixedWidth(50)
        offset_layout.addWidget(offset_value_label)
        self.offset_input.valueChanged.connect(
            lambda value: (offset_value_label.setText(str(value)), self.set_offset(value))
        )
        slider_layout.addLayout(offset_layout)

        layout.addLayout(slider_layout)

    def create_slider(self, label_text, min_val, max_val, default, tick_interval, mapping):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        label = QLabel(label_text)
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(tick_interval)
        slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        value_label = QLabel(str(mapping(default)))
        value_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        slider.valueChanged.connect(lambda value, lbl=value_label, m=mapping: lbl.setText(str(m(value))))
        slider.valueChanged.connect(lambda value, m=mapping: self.update_transformation_parameters())
        layout.addWidget(label)
        layout.addWidget(slider)
        layout.addWidget(value_label)
        return slider, value_label, layout

    def update_transformation_parameters(self):
        # Placeholder for any real-time updates if needed
        pass

    def set_offset(self, value):
        self.offset = value

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            # Reset image_list to contain only the selected single image
            self.image_list = [file_path]
            self.current_image_index = 0
            self.augmented_images = [None] * len(self.image_list)
            self.load_current_image()

    def load_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Load Directory", "")
        if directory:
            self.image_dir = directory
            supported_formats = ['.png', '.jpg', '.jpeg', '.bmp']
            self.image_list = [
                os.path.join(directory, f) for f in os.listdir(directory)
                if os.path.splitext(f)[1].lower() in supported_formats
            ]
            if self.image_list:
                self.current_image_index = 0
                self.augmented_images = [None] * len(self.image_list)
                self.load_current_image()
            else:
                QMessageBox.warning(self, "No Images", "No supported images found in the directory.")

    def load_current_image(self):
        if self.image_list:
            self.current_image_path = self.image_list[self.current_image_index]
            if self.current_image_path in self.processed_images:
                self.image = self.processed_images[self.current_image_path].copy()
                self.original_image = self.image.copy()
                self.display_image(self.image)
            else:
                self.original_image = cv2.imread(self.current_image_path)
                if self.original_image is not None:
                    self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
                    self.image = self.original_image.copy()
                    self.processed_images[self.current_image_path] = self.image.copy()
                    self.display_image(self.image)
                else:
                    QMessageBox.critical(self, "Error", f"Failed to load image: {os.path.basename(self.current_image_path)}")

    def display_image(self, image):
        try:
            height, width, channel = image.shape
            bytes_per_line = 3 * width
            qimage = QImage(
                image.data, width, height, bytes_per_line, QImage.Format_RGB888
            )
            pixmap = QPixmap.fromImage(qimage).scaled(
                int(width * self.zoom_level),
                int(height * self.zoom_level),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(pixmap)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to display image: {e}")

    def resizeEvent(self, event):
        # Update the displayed image size when the window is resized
        if self.image is not None:
            self.display_image(self.image)
        super().resizeEvent(event)

    def zoom_in(self):
        if self.image is not None:
            self.zoom_level *= 1.25
            self.display_image(self.image)

    def zoom_out(self):
        if self.image is not None:
            self.zoom_level /= 1.25
            self.display_image(self.image)

    def reset_image(self):
        if not self.image_list or self.current_image_index < 0:
            QMessageBox.warning(self, "No Image", "No image loaded to reset.")
            return

        try:
            # Reset the current image to the original image
            path = self.image_list[self.current_image_index]
            original_img = cv2.imread(path)

            if original_img is None:
                raise ValueError("Image data is None. Possibly unsupported image format or corrupted file.")

            # Check if the image is too large
            if original_img.shape[0] > 5000 or original_img.shape[1] > 5000:
                raise ValueError("Image dimensions exceed the maximum allowed size of 5000px.")

            # Convert BGR to RGB
            original_img = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
            self.current_image = original_img.copy()  # Set current image to the original
            self.processed_images[path] = original_img.copy()  # Reset processed images

            self.display_image(self.current_image)  # Display the reset image
            QMessageBox.information(self, "Reset Image", "Image has been reset to its original state.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset image: {e}")

    def reset_all(self):
        if self.image_list:
            try:
                # Do not reset zoom level to preserve current zoom
                for idx, path in enumerate(self.image_list):
                    original = cv2.imread(path)
                    if original is not None:
                        original = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
                        self.processed_images[path] = original.copy()
                        self.augmented_images[idx] = original.copy()
                self.load_current_image()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset all images: {e}")

    def apply_hct(self):
        if self.image is not None:
            try:
                # Convert to grayscale for HoughCircles
                gray = cv2.cvtColor(self.image, cv2.COLOR_RGB2GRAY)
                gray = cv2.medianBlur(gray, 5)

                # Get parameters from sliders
                dp = getattr(self, 'dp_slider').value() / 100.0  # Adjusted for float
                minDist = getattr(self, 'minDist_slider').value()
                param1 = getattr(self, 'param1_slider').value()
                param2 = getattr(self, 'param2_slider').value()
                minRadius = getattr(self, 'minRadius_slider').value()
                maxRadius = getattr(self, 'maxRadius_slider').value()

                # Detect circles using HoughCircles
                circles = cv2.HoughCircles(
                    gray, cv2.HOUGH_GRADIENT, dp=dp, minDist=minDist,
                    param1=param1, param2=param2, minRadius=minRadius, maxRadius=maxRadius
                )

                if circles is not None:
                    circles = np.uint16(np.around(circles))
                    for i in circles[0, :]:
                        # Draw the outer circle
                        cv2.circle(self.image, (i[0], i[1]), i[2], (0, 255, 0), 2)
                        # Draw the center of the circle
                        cv2.circle(self.image, (i[0], i[1]), 2, (0, 0, 255), 3)
                    self.processed_images[self.current_image_path] = self.image.copy()
                    self.display_image(self.image)
                else:
                    QMessageBox.information(self, "No Circles", "No circles were detected with the current parameters.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to apply HCT: {e}")

    def apply_hct_all(self):
        if self.image_list:
            for path in self.image_list:
                try:
                    img = cv2.imread(path)
                    if img is not None:
                        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
                        gray = cv2.medianBlur(gray, 5)

                        dp = getattr(self, 'dp_slider').value() / 100.0  # Adjusted for float
                        minDist = getattr(self, 'minDist_slider').value()
                        param1 = getattr(self, 'param1_slider').value()
                        param2 = getattr(self, 'param2_slider').value()
                        minRadius = getattr(self, 'minRadius_slider').value()
                        maxRadius = getattr(self, 'maxRadius_slider').value()

                        circles = cv2.HoughCircles(
                            gray, cv2.HOUGH_GRADIENT, dp=dp, minDist=minDist,
                            param1=param1, param2=param2, minRadius=minRadius, maxRadius=maxRadius
                        )

                        if circles is not None:
                            circles = np.uint16(np.around(circles))
                            for i in circles[0, :]:
                                cv2.circle(img_rgb, (i[0], i[1]), i[2], (0, 255, 0), 2)
                                cv2.circle(img_rgb, (i[0], i[1]), 2, (0, 0, 255), 3)
                        self.processed_images[path] = img_rgb.copy()
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to read image {os.path.basename(path)}")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to apply HCT to {os.path.basename(path)}: {e}")
            self.load_current_image()

    def apply_hct_with_bboxes(self):
        if self.image is not None:
            try:
                # Convert to grayscale for HoughCircles
                gray = cv2.cvtColor(self.image, cv2.COLOR_RGB2GRAY)
                gray = cv2.medianBlur(gray, 5)

                # Get parameters from sliders
                dp = getattr(self, 'dp_slider').value() / 100.0  # Adjusted for float
                minDist = getattr(self, 'minDist_slider').value()
                param1 = getattr(self, 'param1_slider').value()
                param2 = getattr(self, 'param2_slider').value()
                minRadius = getattr(self, 'minRadius_slider').value()
                maxRadius = getattr(self, 'maxRadius_slider').value()

                # Detect circles using HoughCircles
                circles = cv2.HoughCircles(
                    gray, cv2.HOUGH_GRADIENT, dp=dp, minDist=minDist,
                    param1=param1, param2=param2, minRadius=minRadius, maxRadius=maxRadius
                )

                if circles is not None:
                    circles = np.uint16(np.around(circles))
                    for i in circles[0, :]:
                        # Draw the outer circle
                        cv2.circle(self.image, (i[0], i[1]), i[2], (0, 255, 0), 2)
                        # Draw the center of the circle
                        cv2.circle(self.image, (i[0], i[1]), 2, (0, 0, 255), 3)

                        # Define bounding box with offset
                        x = max(i[0] - i[2] - self.offset, 0)
                        y = max(i[1] - i[2] - self.offset, 0)
                        w = min(2 * i[2] + 2 * self.offset, self.image.shape[1] - x)
                        h_box = min(2 * i[2] + 2 * self.offset, self.image.shape[0] - y)

                        # Draw bounding box
                        cv2.rectangle(self.image, (x, y), (x + w, y + h_box), (255, 0, 0), 2)

                        # Store bounding box with class number
                        class_num = self.class_number_selector.value()
                        if self.current_image_path not in self.bounding_boxes:
                            self.bounding_boxes[self.current_image_path] = []
                        self.bounding_boxes[self.current_image_path].append((x, y, w, h_box, class_num))

                    self.processed_images[self.current_image_path] = self.image.copy()
                    self.display_image(self.image)
                else:
                    QMessageBox.information(self, "No Circles", "No circles were detected with the current parameters.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to apply HCT with bounding boxes: {e}")

    def apply_hct_with_bboxes_all(self):
        if self.image_list:
            for path in self.image_list:
                try:
                    img = cv2.imread(path)
                    if img is not None:
                        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
                        gray = cv2.medianBlur(gray, 5)

                        dp = getattr(self, 'dp_slider').value() / 100.0  # Adjusted for float
                        minDist = getattr(self, 'minDist_slider').value()
                        param1 = getattr(self, 'param1_slider').value()
                        param2 = getattr(self, 'param2_slider').value()
                        minRadius = getattr(self, 'minRadius_slider').value()
                        maxRadius = getattr(self, 'maxRadius_slider').value()

                        circles = cv2.HoughCircles(
                            gray, cv2.HOUGH_GRADIENT, dp=dp, minDist=minDist,
                            param1=param1, param2=param2, minRadius=minRadius, maxRadius=maxRadius
                        )

                        if circles is not None:
                            circles = np.uint16(np.around(circles))
                            for i in circles[0, :]:
                                cv2.circle(img_rgb, (i[0], i[1]), i[2], (0, 255, 0), 2)
                                cv2.circle(img_rgb, (i[0], i[1]), 2, (0, 0, 255), 3)

                                # Define bounding box with offset
                                x = max(i[0] - i[2] - self.offset, 0)
                                y = max(i[1] - i[2] - self.offset, 0)
                                w = min(2 * i[2] + 2 * self.offset, img_rgb.shape[1] - x)
                                h_box = min(2 * i[2] + 2 * self.offset, img_rgb.shape[0] - y)

                                # Draw bounding box
                                cv2.rectangle(img_rgb, (x, y), (x + w, y + h_box), (255, 0, 0), 2)

                                # Store bounding box with class number
                                class_num = self.class_number_selector.value()
                                if path not in self.bounding_boxes:
                                    self.bounding_boxes[path] = []
                                self.bounding_boxes[path].append((x, y, w, h_box, class_num))

                        self.processed_images[path] = img_rgb.copy()
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to read image {os.path.basename(path)}")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to apply HCT with bounding boxes to {os.path.basename(path)}: {e}")
            self.load_current_image()

    def save_image(self):
        if self.image is not None:
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Image", "", "PNG files (*.png);;JPEG files (*.jpg *.jpeg);;BMP files (*.bmp)"
            )
            if save_path:
                try:
                    # Convert RGB to BGR before saving with OpenCV
                    img_bgr = cv2.cvtColor(self.image, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(save_path, img_bgr)
                    QMessageBox.information(self, "Saved", f"Image saved to {save_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save image: {e}")

    def save_all(self):
        if not self.image_list:
            QMessageBox.warning(self, "No Images", "No images loaded to save.")
            return

        save_folder = QFileDialog.getExistingDirectory(self, "Select Save Folder", "")
        if not save_folder:
            return

        try:
            for path in self.image_list:
                transformed_img = self.processed_images.get(path, None)
                if transformed_img is not None:
                    save_path = os.path.join(save_folder, os.path.basename(path))
                    # Convert RGB to BGR before saving
                    img_bgr = cv2.cvtColor(transformed_img, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(save_path, img_bgr)
            QMessageBox.information(self, "Save All", "All images have been saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save all images: {e}")

    def save_annotations(self):
        if not self.bounding_boxes.get(self.current_image_path, []):
            QMessageBox.warning(self, "No Annotations", "No annotations to save.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Annotations", "", "Text files (*.txt)"
        )
        if save_path:
            try:
                with open(save_path, 'w') as f:
                    # Ensure the image is loaded to get dimensions
                    if self.image is not None:
                        image_height, image_width = self.image.shape[:2]
                    else:
                        raise ValueError("No image loaded to retrieve dimensions.")

                    for box in self.bounding_boxes[self.current_image_path]:
                        x, y, w, h_box, class_num = box

                        # Calculate normalized coordinates
                        x_center = (x + w / 2.0) / image_width
                        y_center = (y + h_box / 2.0) / image_height
                        width_norm = w / image_width
                        height_norm = h_box / image_height

                        # Write in YOLO format
                        f.write(f"{class_num} {x_center:.6f} {y_center:.6f} {width_norm:.6f} {height_norm:.6f}\n")
                QMessageBox.information(self, "Saved", f"Annotations saved to {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save annotations:\n{e}")

    def save_all_annotations(self):
        if not self.bounding_boxes:
            QMessageBox.warning(self, "No Annotations", "No annotations to save.")
            return

        save_folder = QFileDialog.getExistingDirectory(self, "Select Save Folder for Annotations", "")
        if not save_folder:
            return

        try:
            for path, boxes in self.bounding_boxes.items():
                annotation_path = os.path.join(save_folder, os.path.splitext(os.path.basename(path))[0] + ".txt")
                with open(annotation_path, 'w') as f:
                    # Retrieve the processed image to get dimensions
                    if path in self.processed_images and self.processed_images[path] is not None:
                        image_height, image_width = self.processed_images[path].shape[:2]
                    else:
                        # Attempt to load the image to get dimensions
                        img = cv2.imread(path)
                        if img is not None:
                            image_height, image_width = img.shape[:2]
                        else:
                            raise ValueError(f"Cannot load image {path} to get dimensions.")

                    for box in boxes:
                        x, y, w, h_box, class_num = box

                        # Calculate normalized coordinates
                        x_center = (x + w / 2.0) / image_width
                        y_center = (y + h_box / 2.0) / image_height
                        width_norm = w / image_width
                        height_norm = h_box / image_height

                        # Write in YOLO format
                        f.write(f"{class_num} {x_center:.6f} {y_center:.6f} {width_norm:.6f} {height_norm:.6f}\n")
            QMessageBox.information(self, "Save All Annotations", "All annotations have been saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save annotations for some images:\n{e}")

    def reset_sliders(self):
        sliders = ['dp', 'minDist', 'param1', 'param2', 'minRadius', 'maxRadius']
        defaults = [100, 20, 50, 30, 0, 0]  # dp default adjusted to 100 (1.0)
        for slider, default in zip(sliders, defaults):
            getattr(self, f"{slider}_slider").setValue(default)
        self.class_number_selector.setValue(0)
        self.offset_input.setValue(10)
        QMessageBox.information(self, "Sliders Reset", "All sliders have been reset to default values.")

    def show_help(self):
        help_text = (
            "HCT & Auto Labeling Help:\n\n"
            "Use the buttons to perform various actions such as loading images, applying HCT transformations, "
            "saving images and annotations, and navigating through images.\n\n"
            "Adjust the sliders to set parameters for HCT transformations.\n"
            "Use the 'Apply' buttons to apply transformations to the current image or all images.\n"
            "Save your work using the 'Save' buttons.\n\n"
            "Keyboard Shortcuts:\n"
            "- Press 'A' to go to the previous image.\n"
            "- Press 'D' to go to the next image.\n"
            "- Zoom In: Ctrl + +\n"
            "- Zoom Out: Ctrl + -\n\n"
            "Bounding Boxes:\n"
            "- 'Apply HCT with BBoxes' will detect circles and draw bounding boxes around them.\n"
            "- Adjust the 'Bounding Box Offset' to change the size of the bounding boxes.\n"
            "- Set the 'Class Number' for each bounding box."
        )
        QMessageBox.information(self, "Help", help_text)

    def previous_image(self):
        if self.image_list:
            if self.current_image_index > 0:
                self.current_image_index -= 1
                self.load_current_image()
            else:
                QMessageBox.information(self, "Start", "This is the first image.")
        else:
            QMessageBox.warning(self, "No Images", "No images loaded.")

    def next_image(self):
        if self.image_list:
            if self.current_image_index < len(self.image_list) - 1:
                self.current_image_index += 1
                self.load_current_image()
            else:
                QMessageBox.information(self, "End", "This is the last image.")
        else:
            QMessageBox.warning(self, "No Images", "No images loaded.")


import sys
import os
import cv2
import numpy as np
import logging
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QScrollArea, QSlider, QSpinBox, QCheckBox, QFileDialog,
    QMessageBox, QSizePolicy
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='app.log',
                    format='%(asctime)s - %(levelname)s - %(message)s')

class ImageAugmentationTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)

        # Initialize variables
        self.original_image = None
        self.current_image = None
        self.image_list = []
        self.current_image_index = 0
        self.zoom_level = 1.0
        self.image_dir = ''
        self.augmented_images = []
        self.processed_images = {}

        # Setup UI
        self.init_ui()

    def init_ui(self):
        try:
            main_layout = QVBoxLayout()
            self.setLayout(main_layout)

            # Image display
            self.image_label = QLabel()
            self.image_label.setAlignment(Qt.AlignCenter)
            self.image_label.setFocusPolicy(Qt.NoFocus)
            self.scroll_area = QScrollArea()
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setWidget(self.image_label)
            main_layout.addWidget(self.scroll_area, stretch=8)

            # Buttons and sliders
            self.create_buttons(main_layout)
            self.create_sliders(layout=main_layout)

            logging.debug("ImageAugmentationTab UI initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize UI: {e}")
            QMessageBox.critical(self, "Error", f"Failed to initialize UI: {e}")

    def create_buttons(self, layout):
        try:
            button_row = QHBoxLayout()
            button_row.setSpacing(5)

            buttons = [
                ('Load Image', self.load_image),
                ('Load Directory', self.load_directory),
                ('Apply AUG', self.apply_augmentation),
                ('Apply AUG To All', self.apply_augmentation_all),
                ('Save Image', self.save_image),
                ('Save All', self.save_all_images),
                ('Reset Image', self.reset_image),
                ('Reset All', self.reset_all_images),
                ('Reset Sliders', self.reset_sliders),
                ('Previous', self.previous_image),
                ('Next', self.next_image),
                ('Zoom In', self.zoom_in),
                ('Zoom Out', self.zoom_out),
                ('?', self.show_help)
            ]

            for text, method in buttons:
                button = QPushButton(text)
                if text == '?':
                    button.setFixedSize(30, 30)
                    button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                    button.setToolTip("Show Help")
                    button.setStyleSheet("font-weight: bold;")
                else:
                    button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
                    button.setToolTip(f"{text} Button")

                # Connect button to method
                try:
                    button.clicked.connect(method)
                except AttributeError as attr_err:
                    logging.error(f"Failed to connect button '{text}' to method '{method}': {attr_err}")
                    QMessageBox.critical(self, "Error", f"Failed to connect button '{text}' to its function.")
                    return

                button_row.addWidget(button)

            button_row.addStretch()
            layout.addLayout(button_row)

            logging.debug("Buttons created and connected successfully.")
        except Exception as e:
            logging.error(f"Failed to create buttons: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create buttons: {e}")

    def create_sliders(self, layout):
        try:
            slider_layout = QVBoxLayout()
            slider_layout.setSpacing(5)

            # Define slider configurations
            sliders_info = [
                {'name': 'white_balance', 'label': 'White Balance', 'min': -100, 'max': 100, 'default': 0, 'factor': 1},
                {'name': 'hsv_h', 'label': 'HSV Hue', 'min': -180, 'max': 180, 'default': 0, 'factor': 1},
                {'name': 'hsv_s', 'label': 'HSV Saturation', 'min': -100, 'max': 100, 'default': 0, 'factor': 1},
                {'name': 'hsv_v', 'label': 'HSV Value', 'min': -100, 'max': 100, 'default': 0, 'factor': 1},
                {'name': 'degrees', 'label': 'Rotation Degrees', 'min': -180, 'max': 180, 'default': 0, 'factor': 1},
                {'name': 'translate', 'label': 'Translate', 'min': -100, 'max': 100, 'default': 0, 'factor': 1},
                {'name': 'scale', 'label': 'Scale (%)', 'min': 50, 'max': 150, 'default': 100, 'factor': 1},
                {'name': 'shear', 'label': 'Shear', 'min': -45, 'max': 45, 'default': 0, 'factor': 1},
                {'name': 'noise', 'label': 'Noise Level', 'min': 0, 'max': 100, 'default': 0, 'factor': 1},
            ]

            for info in sliders_info:
                slider = QSlider(Qt.Horizontal)
                slider.setMinimum(info['min'])
                slider.setMaximum(info['max'])
                slider.setValue(info['default'])
                slider.setObjectName(info['name'])
                slider.setTickPosition(QSlider.TicksBelow)
                slider.setTickInterval((info['max'] - info['min']) // 10)

                value_label = QLabel(f"{info['default'] * info['factor']:.2f}")
                value_label.setFixedWidth(60)

                # Connect slider to update label
                slider.valueChanged.connect(
                    lambda value, s=slider, l=value_label, f=info['factor']: self.update_value_label(s, l, f)
                )

                h_layout = QHBoxLayout()
                param_label = QLabel(info['label'])
                param_label.setFixedWidth(150)
                h_layout.addWidget(param_label)
                h_layout.addWidget(slider)
                h_layout.addWidget(value_label)
                slider_layout.addLayout(h_layout)

                # Assign sliders and labels to attributes
                setattr(self, f"{info['name']}_slider", slider)
                setattr(self, f"{info['name']}_value_label", value_label)

            # Combine Flip Checkboxes and Padding Controls in the Same Row
            combined_layout = QHBoxLayout()
            combined_layout.setSpacing(10)  # Minimal spacing

            # Flip Checkboxes
            flip_layout = QHBoxLayout()
            flip_layout.setSpacing(5)
            self.flipud_checkbox = QCheckBox('Flip Up-Down')
            self.fliplr_checkbox = QCheckBox('Flip Left-Right')
            flip_layout.addWidget(self.flipud_checkbox)
            flip_layout.addWidget(self.fliplr_checkbox)

            # Padding Controls
            padding_layout = QHBoxLayout()
            padding_layout.setSpacing(5)

            self.padding_checkbox = QCheckBox("Add Padding")
            self.padding_checkbox.stateChanged.connect(self.toggle_padding)
            padding_layout.addWidget(self.padding_checkbox)

            padding_width_label = QLabel("Width (px):")
            padding_layout.addWidget(padding_width_label)

            self.padding_width_spin = QSpinBox()
            self.padding_width_spin.setMinimum(0)
            self.padding_width_spin.setMaximum(10000)  # Allow large padding if needed
            self.padding_width_spin.setValue(0)
            self.padding_width_spin.setEnabled(False)
            padding_layout.addWidget(self.padding_width_spin)

            padding_height_label = QLabel("Height (px):")
            padding_layout.addWidget(padding_height_label)

            self.padding_height_spin = QSpinBox()
            self.padding_height_spin.setMinimum(0)
            self.padding_height_spin.setMaximum(10000)  # Allow large padding if needed
            self.padding_height_spin.setValue(0)
            self.padding_height_spin.setEnabled(False)
            padding_layout.addWidget(self.padding_height_spin)

            # Add Flip and Padding to Combined Layout
            combined_layout.addLayout(flip_layout)
            combined_layout.addStretch()
            combined_layout.addLayout(padding_layout)

            slider_layout.addLayout(combined_layout)
            layout.addLayout(slider_layout)

            logging.debug("Sliders created and connected successfully.")
        except Exception as e:
            logging.error(f"Failed to create sliders: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create sliders: {e}")

    def update_value_label(self, slider, label, factor):
        try:
            value = slider.value() * factor
            label.setText(f"{value:.2f}")
        except Exception as e:
            logging.error(f"Failed to update slider label: {e}")
            label.setText("Error")

    def toggle_padding(self, state):
        try:
            enabled = state == Qt.Checked
            self.padding_width_spin.setEnabled(enabled)
            self.padding_height_spin.setEnabled(enabled)
            logging.debug(f"Padding toggled: {'Enabled' if enabled else 'Disabled'}.")
        except Exception as e:
            logging.error(f"Failed to toggle padding: {e}")

    def load_image(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Load Image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
            )
            if file_path:
                logging.debug(f"Loading image from {file_path}")
                self.original_image = cv2.imread(file_path)
                if self.original_image is None:
                    raise ValueError("Image data is None. Possibly unsupported image format or corrupted file.")
                if self.original_image.shape[0] > 5000 or self.original_image.shape[1] > 5000:
                    raise ValueError("Image dimensions exceed the maximum allowed size of 5000px.")
                self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
                self.current_image = self.original_image.copy()
                self.image_list = [file_path]
                self.current_image_index = 0
                self.augmented_images = [None]  # Initialize with None
                self.display_image(self.current_image)
                logging.debug("Image loaded and displayed successfully.")
        except Exception as e:
            logging.error(f"Failed to load image: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load image: {e}")

    def load_directory(self):
        try:
            directory = QFileDialog.getExistingDirectory(self, "Load Directory", "")
            if directory:
                logging.debug(f"Loading directory: {directory}")
                supported_formats = ['.png', '.jpg', '.jpeg', '.bmp']
                self.image_list = [
                    os.path.join(directory, f) for f in os.listdir(directory)
                    if os.path.splitext(f)[1].lower() in supported_formats
                ]
                if self.image_list:
                    self.current_image_index = 0
                    self.augmented_images = [None] * len(self.image_list)
                    self.load_current_image()
                    logging.debug("Directory loaded successfully.")
                else:
                    QMessageBox.warning(self, "No Images", "No supported images found in the directory.")
        except Exception as e:
            logging.error(f"Failed to load directory: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load directory: {e}")

    def load_current_image(self):
        try:
            if self.image_list:
                self.current_image_path = self.image_list[self.current_image_index]
                logging.debug(f"Loading current image: {self.current_image_path}")
                if self.augmented_images[self.current_image_index] is not None:
                    self.current_image = self.augmented_images[self.current_image_index].copy()
                    self.display_image(self.current_image)
                else:
                    self.original_image = cv2.imread(self.current_image_path)
                    if self.original_image is None:
                        raise ValueError("Image data is None. Possibly unsupported image format or corrupted file.")
                    if self.original_image.shape[0] > 5000 or self.original_image.shape[1] > 5000:
                        raise ValueError("Image dimensions exceed the maximum allowed size of 5000px.")
                    self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
                    self.current_image = self.original_image.copy()
                    self.augmented_images[self.current_image_index] = self.current_image.copy()
                    self.display_image(self.current_image)
                logging.debug("Current image loaded and displayed successfully.")
        except Exception as e:
            logging.error(f"Failed to load current image: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load image: {e}")

    def display_image(self, image):
        try:
            if image is None:
                raise ValueError("Image is None.")
            if len(image.shape) != 3 or image.shape[2] != 3:
                raise ValueError("Image must be a 3-channel RGB image.")

            height, width, channel = image.shape
            bytes_per_line = 3 * width

            if not image.flags['C_CONTIGUOUS']:
                image = np.ascontiguousarray(image)

            qimage = QImage(
                image.data, width, height, bytes_per_line, QImage.Format_RGB888
            )
            if qimage.isNull():
                raise ValueError("QImage is null. Possibly unsupported image format.")

            pixmap = QPixmap.fromImage(qimage)
            # Limit zoom to prevent excessive scaling
            if self.zoom_level > 5.0:
                self.zoom_level = 5.0
            elif self.zoom_level < 0.1:
                self.zoom_level = 0.1

            scaled_pixmap = pixmap.scaled(
                int(width * self.zoom_level),
                int(height * self.zoom_level),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.adjustSize()
            logging.debug("Image displayed successfully.")
        except Exception as e:
            logging.error(f"Failed to display image: {e}")
            QMessageBox.critical(self, "Error", f"Failed to display image: {e}")

    def apply_augmentation(self):
        try:
            if not self.image_list:
                QMessageBox.warning(self, "No Image", "No image loaded to apply augmentations.")
                return

            # Start with the original image to prevent cumulative transformations
            path = self.image_list[self.current_image_index]
            original_img = cv2.imread(path)
            if original_img is None:
                raise ValueError("Original image data is None. Possibly unsupported image format or corrupted file.")
            if original_img.shape[0] > 5000 or original_img.shape[1] > 5000:
                raise ValueError("Image dimensions exceed the maximum allowed size of 5000px.")
            original_img = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)

            img = original_img.copy()

            # Apply white balance
            wb_value = self.white_balance_slider.value()
            if wb_value != 0:
                if wb_value > 0:
                    img = cv2.convertScaleAbs(img, alpha=1, beta=wb_value * 2.55)
                elif wb_value < 0:
                    factor = 1 + (wb_value / 100.0)
                    img = cv2.convertScaleAbs(img, alpha=factor, beta=0)

            # Apply HSV adjustments
            hsv_h = self.hsv_h_slider.value()
            hsv_s = self.hsv_s_slider.value() / 100.0  # Scale saturation
            hsv_v = self.hsv_v_slider.value() / 100.0  # Scale value
            if hsv_h != 0 or hsv_s != 0 or hsv_v != 0:
                hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV).astype(float)
                hsv[:, :, 0] = (hsv[:, :, 0] + hsv_h) % 180
                hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1 + hsv_s), 0, 255)
                hsv[:, :, 2] = np.clip(hsv[:, :, 2] * (1 + hsv_v), 0, 255)
                hsv = hsv.astype(np.uint8)
                img = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

            # Apply rotation
            degrees = self.degrees_slider.value()
            if degrees != 0:
                (h, w) = img.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, degrees, 1.0)
                img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

            # Apply translation
            translate = self.translate_slider.value()
            if translate != 0:
                M = np.float32([[1, 0, translate], [0, 1, translate]])
                (h, w) = img.shape[:2]
                img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

            # Apply scaling
            scale = self.scale_slider.value() / 100.0
            if scale != 1.0:
                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)

            # Apply shear
            shear = self.shear_slider.value()
            if shear != 0:
                shear_rad = np.radians(shear)
                M = np.float32([
                    [1, np.tan(shear_rad), 0],
                    [0, 1, 0]
                ])
                (h, w) = img.shape[:2]
                new_width = w + int(abs(np.tan(shear_rad)) * h)
                img = cv2.warpAffine(img, M, (new_width, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

            # Apply noise
            noise_level = self.noise_slider.value()
            if noise_level > 0:
                noise = np.random.randint(0, noise_level, img.shape, dtype='uint8')
                img = cv2.add(img, noise)

            # Apply flipping
            if self.flipud_checkbox.isChecked():
                img = cv2.flip(img, 0)  # Flip vertically
            if self.fliplr_checkbox.isChecked():
                img = cv2.flip(img, 1)  # Flip horizontally

            # Apply padding if enabled
            if self.padding_checkbox.isChecked():
                desired_width = self.padding_width_spin.value()
                desired_height = self.padding_height_spin.value()

                if desired_width < img.shape[1] or desired_height < img.shape[0]:
                    QMessageBox.warning(self, "Invalid Padding", "Desired padding dimensions must be greater than or equal to the current image dimensions.")
                else:
                    img = self.apply_padding(img, desired_width, desired_height)

            # Update augmented_images list
            self.augmented_images[self.current_image_index] = img.copy()
            self.current_image = img.copy()
            self.display_image(self.current_image)
            logging.debug("Augmentation applied successfully.")
            QMessageBox.information(self, "Augmentation Applied", "Augmentations have been applied to the current image.")
        except Exception as e:
            logging.error(f"Failed to apply augmentation: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply augmentation: {e}")

    def apply_augmentation_all(self):
        try:
            if not self.image_list:
                QMessageBox.warning(self, "No Images", "No images loaded to apply augmentations.")
                return

            for idx, path in enumerate(self.image_list):
                img = cv2.imread(path)
                if img is not None:
                    if img.shape[0] > 5000 or img.shape[1] > 5000:
                        logging.warning(f"Image {path} exceeds maximum dimensions. Skipping.")
                        continue
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                    # Start with the original image to prevent cumulative transformations
                    aug_img = img_rgb.copy()

                    # Apply white balance
                    wb_value = self.white_balance_slider.value()
                    if wb_value != 0:
                        if wb_value > 0:
                            aug_img = cv2.convertScaleAbs(aug_img, alpha=1, beta=wb_value * 2.55)
                        elif wb_value < 0:
                            factor = 1 + (wb_value / 100.0)
                            aug_img = cv2.convertScaleAbs(aug_img, alpha=factor, beta=0)

                    # Apply HSV adjustments
                    hsv_h = self.hsv_h_slider.value()
                    hsv_s = self.hsv_s_slider.value() / 100.0  # Scale saturation
                    hsv_v = self.hsv_v_slider.value() / 100.0  # Scale value
                    if hsv_h != 0 or hsv_s != 0 or hsv_v != 0:
                        hsv = cv2.cvtColor(aug_img, cv2.COLOR_RGB2HSV).astype(float)
                        hsv[:, :, 0] = (hsv[:, :, 0] + hsv_h) % 180
                        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1 + hsv_s), 0, 255)
                        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * (1 + hsv_v), 0, 255)
                        hsv = hsv.astype(np.uint8)
                        aug_img = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

                    # Apply rotation
                    degrees = self.degrees_slider.value()
                    if degrees != 0:
                        (h, w) = aug_img.shape[:2]
                        center = (w // 2, h // 2)
                        M = cv2.getRotationMatrix2D(center, degrees, 1.0)
                        aug_img = cv2.warpAffine(aug_img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

                    # Apply translation
                    translate = self.translate_slider.value()
                    if translate != 0:
                        M = np.float32([[1, 0, translate], [0, 1, translate]])
                        (h, w) = aug_img.shape[:2]
                        aug_img = cv2.warpAffine(aug_img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

                    # Apply scaling
                    scale = self.scale_slider.value() / 100.0
                    if scale != 1.0:
                        aug_img = cv2.resize(aug_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)

                    # Apply shear
                    shear = self.shear_slider.value()
                    if shear != 0:
                        shear_rad = np.radians(shear)
                        M = np.float32([
                            [1, np.tan(shear_rad), 0],
                            [0, 1, 0]
                        ])
                        (h, w) = aug_img.shape[:2]
                        new_width = w + int(abs(np.tan(shear_rad)) * h)
                        aug_img = cv2.warpAffine(aug_img, M, (new_width, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

                    # Apply noise
                    noise_level = self.noise_slider.value()
                    if noise_level > 0:
                        noise = np.random.randint(0, noise_level, aug_img.shape, dtype='uint8')
                        aug_img = cv2.add(aug_img, noise)

                    # Apply flipping
                    if self.flipud_checkbox.isChecked():
                        aug_img = cv2.flip(aug_img, 0)  # Flip vertically
                    if self.fliplr_checkbox.isChecked():
                        aug_img = cv2.flip(aug_img, 1)  # Flip horizontally

                    # Apply padding if enabled
                    if self.padding_checkbox.isChecked():
                        desired_width = self.padding_width_spin.value()
                        desired_height = self.padding_height_spin.value()

                        if desired_width < aug_img.shape[1] or desired_height < aug_img.shape[0]:
                            logging.warning(f"Desired padding dimensions for image {path} are smaller than current dimensions. Skipping padding.")
                        else:
                            aug_img = self.apply_padding(aug_img, desired_width, desired_height)

                    # Update augmented_images list
                    self.augmented_images[idx] = aug_img.copy()
                    logging.debug(f"Augmentation applied to image: {path}")
                else:
                    logging.warning(f"Failed to read image {path}. Skipping.")

            self.load_current_image()
            QMessageBox.information(self, "Augmentation Applied", "Augmentations have been applied to all images.")
            logging.debug("Augmentation applied to all images successfully.")
        except Exception as e:
            logging.error(f"Failed to apply augmentation to all images: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply augmentation to all images: {e}")

    def apply_padding(self, img, desired_width, desired_height):
        try:
            original_height, original_width = img.shape[:2]

            # Calculate required padding
            pad_width = max(desired_width - original_width, 0)
            pad_height = max(desired_height - original_height, 0)

            pad_left = pad_width // 2
            pad_right = pad_width - pad_left
            pad_top = pad_height // 2
            pad_bottom = pad_height - pad_top

            if pad_width > 0 or pad_height > 0:
                img = cv2.copyMakeBorder(
                    img,
                    top=pad_top,
                    bottom=pad_bottom,
                    left=pad_left,
                    right=pad_right,
                    borderType=cv2.BORDER_CONSTANT,
                    value=[255, 255, 255]  # White padding
                )
                logging.debug(f"Applied padding: Left={pad_left}px, Right={pad_right}px, Top={pad_top}px, Bottom={pad_bottom}px")
            else:
                logging.debug("No padding applied as desired size is smaller or equal to original size.")

            return img
        except Exception as e:
            logging.error(f"Failed to apply padding: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply padding: {e}")
            return img  # Return original image if padding fails

    def save_image(self):
        try:
            if self.current_image is None:
                QMessageBox.warning(self, "No Image", "No augmented image to save.")
                return
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Augmented Image", "", "PNG files (*.png);;JPEG files (*.jpg *.jpeg);;BMP files (*.bmp)"
            )
            if save_path:
                img_bgr = cv2.cvtColor(self.current_image, cv2.COLOR_RGB2BGR)
                cv2.imwrite(save_path, img_bgr)
                QMessageBox.information(self, "Saved", f"Image saved to {save_path}")
                logging.debug(f"Image saved to {save_path}")
        except Exception as e:
            logging.error(f"Failed to save image: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save image: {e}")

    def save_all_images(self):
        try:
            if not self.image_list:
                QMessageBox.warning(self, "No Images", "No images loaded to save.")
                return

            save_folder = QFileDialog.getExistingDirectory(self, "Select Save Folder", "")
            if not save_folder:
                return

            for idx, path in enumerate(self.image_list):
                if idx < len(self.augmented_images) and self.augmented_images[idx] is not None:
                    img_rgb = self.augmented_images[idx]
                else:
                    img = cv2.imread(path)
                    if img is not None:
                        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    else:
                        logging.warning(f"Failed to read image {path}. Skipping.")
                        continue

                img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                save_path = os.path.join(save_folder, os.path.basename(path))
                cv2.imwrite(save_path, img_bgr)
                logging.debug(f"Image saved to {save_path}")

            QMessageBox.information(self, "Save All", "All augmented images have been saved successfully.")
            logging.debug("All augmented images saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save all images: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save all images: {e}")

    def reset_image(self):
        try:
            if not self.image_list:
                QMessageBox.warning(self, "No Image", "No image loaded to reset.")
                return

            # Reset the current image to original
            path = self.image_list[self.current_image_index]
            self.original_image = cv2.imread(path)
            if self.original_image is None:
                raise ValueError("Image data is None. Possibly unsupported image format or corrupted file.")
            if self.original_image.shape[0] > 5000 or self.original_image.shape[1] > 5000:
                raise ValueError("Image dimensions exceed the maximum allowed size of 5000px.")
            self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
            self.current_image = self.original_image.copy()
            self.augmented_images[self.current_image_index] = self.current_image.copy()
            self.display_image(self.current_image)
            QMessageBox.information(self, "Reset Image", "Image has been reset to its original state.")
            logging.debug("Image reset to original successfully.")
        except Exception as e:
            logging.error(f"Failed to reset image: {e}")
            QMessageBox.critical(self, "Error", f"Failed to reset image: {e}")

    def reset_all_images(self):
        try:
            if not self.image_list:
                QMessageBox.warning(self, "No Images", "No images loaded to reset.")
                return

            for idx, path in enumerate(self.image_list):
                img = cv2.imread(path)
                if img is not None:
                    if img.shape[0] > 5000 or img.shape[1] > 5000:
                        logging.warning(f"Image {path} exceeds maximum dimensions. Skipping.")
                        continue
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    self.augmented_images[idx] = img_rgb.copy()
                    logging.debug(f"Image reset: {path}")
                else:
                    logging.warning(f"Failed to read image {path}. Skipping.")

            self.load_current_image()
            QMessageBox.information(self, "Reset All", "All images have been reset to their original state.")
            logging.debug("All images reset successfully.")
        except Exception as e:
            logging.error(f"Failed to reset all images: {e}")
            QMessageBox.critical(self, "Error", f"Failed to reset all images: {e}")

    def zoom_in(self):
        try:
            if self.current_image is not None:
                self.zoom_level *= 1.25
                if self.zoom_level > 5.0:
                    self.zoom_level = 5.0
                self.display_image(self.current_image)
                logging.debug(f"Zoomed in to {self.zoom_level}x.")
        except Exception as e:
            logging.error(f"Failed to zoom in: {e}")
            QMessageBox.critical(self, "Error", f"Failed to zoom in: {e}")

    def zoom_out(self):
        try:
            if self.current_image is not None:
                self.zoom_level /= 1.25
                if self.zoom_level < 0.1:
                    self.zoom_level = 0.1
                self.display_image(self.current_image)
                logging.debug(f"Zoomed out to {self.zoom_level}x.")
        except Exception as e:
            logging.error(f"Failed to zoom out: {e}")
            QMessageBox.critical(self, "Error", f"Failed to zoom out: {e}")

    def reset_sliders(self):
        try:
            # Reset all sliders to default values
            self.white_balance_slider.setValue(0)
            self.hsv_h_slider.setValue(0)
            self.hsv_s_slider.setValue(0)
            self.hsv_v_slider.setValue(0)
            self.degrees_slider.setValue(0)
            self.translate_slider.setValue(0)
            self.scale_slider.setValue(100)
            self.shear_slider.setValue(0)
            self.noise_slider.setValue(0)

            # Reset checkboxes
            self.flipud_checkbox.setChecked(False)
            self.fliplr_checkbox.setChecked(False)
            self.padding_checkbox.setChecked(False)

            # Reset padding spin boxes
            self.padding_width_spin.setValue(0)
            self.padding_height_spin.setValue(0)

            # Reset zoom level
            self.zoom_level = 1.0
            if self.current_image is not None:
                self.display_image(self.current_image)

            QMessageBox.information(self, "Sliders Reset", "All sliders and controls have been reset to default values.")
            logging.debug("All sliders and controls reset successfully.")
        except Exception as e:
            logging.error(f"Failed to reset sliders: {e}")
            QMessageBox.critical(self, "Error", f"Failed to reset sliders: {e}")

    def show_help(self):
        help_text = (
            "Image Augmentation Help:\n\n"
            "1. **Load Image**: Load a single image for augmentation.\n"
            "2. **Load Directory**: Load all supported images from a directory.\n"
            "3. **Apply AUG**: Apply the selected augmentations to the current image.\n"
            "4. **Apply AUG To All**: Apply the selected augmentations to all loaded images.\n"
            "5. **Save Image**: Save the augmented version of the current image.\n"
            "6. **Save All**: Save all augmented images to a selected folder.\n"
            "7. **Reset Image**: Reset the current image to its original state.\n"
            "8. **Reset All**: Reset all images to their original states.\n"
            "9. **Reset Sliders**: Reset all augmentation parameters to their default values.\n"
            "10. **Previous/Next**: Navigate through loaded images.\n"
            "11. **Zoom In/Out**: Adjust the zoom level of the displayed image.\n\n"
            "**Augmentation Parameters:**\n"
            "- **White Balance**: Adjust the overall White Balance of the image.\n"
            "- **HSV Hue/Saturation/Value**: Modify the color properties.\n"
            "- **Rotation Degrees**: Rotate the image by the specified degrees.\n"
            "- **Translate**: Shift the image horizontally and vertically.\n"
            "- **Scale (%)**: Resize the image by the specified percentage.\n"
            "- **Shear**: Apply a shearing transformation.\n"
            "- **Noise Level**: Add random noise to the image.\n\n"
            "**Flipping Options:**\n"
            "- **Flip Up-Down**: Vertically flip the image.\n"
            "- **Flip Left-Right**: Horizontally flip the image.\n\n"
            "**Padding:**\n"
            "- **Add Padding**: When checked, specify the desired total width and height in pixels.\n"
            "- **Width (px)** and **Height (px)**: Enter the desired total dimensions. The application will calculate the necessary padding to reach these sizes.\n\n"
            "Ensure that the desired padding dimensions are greater than or equal to the original image dimensions to prevent unexpected behavior."
        )
        QMessageBox.information(self, "Help", help_text)
        logging.debug("Help dialog shown.")

    def previous_image(self):
        try:
            if self.image_list and self.current_image_index > 0:
                self.current_image_index -= 1
                self.load_current_image()
                logging.debug(f"Moved to previous image: Index {self.current_image_index}")
            else:
                QMessageBox.information(self, "Start", "This is the first image.")
        except Exception as e:
            logging.error(f"Failed to go to previous image: {e}")
            QMessageBox.critical(self, "Error", f"Failed to go to previous image: {e}")

    def next_image(self):
        try:
            if self.image_list and self.current_image_index < len(self.image_list) - 1:
                self.current_image_index += 1
                self.load_current_image()
                logging.debug(f"Moved to next image: Index {self.current_image_index}")
            else:
                QMessageBox.information(self, "End", "This is the last image.")
        except Exception as e:
            logging.error(f"Failed to go to next image: {e}")
            QMessageBox.critical(self, "Error", f"Failed to go to next image: {e}")


def main():
    app = QApplication(sys.argv)
    window = ComprehensiveImageEditor()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()



