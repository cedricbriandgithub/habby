import sys
from src_GUI import Main_windows_1
from PyQt5.QtWidgets import QMainWindow, QApplication

def main():

    # create app
    app = QApplication(sys.argv)
    # create windows
    ex = Main_windows_1.MainWindows()

    # close
    sys.exit(app.exec_())
    #os._exit()

if __name__ == '__main__':
    main()