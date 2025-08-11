from GUI import main_app
from sys import argv

def main():
    # instantiate our app with sys.argv
    app = main_app.qt.QtWidgets.QApplication(argv)
    # instantiate main window, passing in our app instance
    window = main_app.MainWindow(app)
    # Show the window
    window.show()
    # Execute the app
    app.exec()


if __name__ == '__main__':
    main()
