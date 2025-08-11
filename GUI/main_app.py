from GUI import qt_classes as qt
import sys
from functools import partial
from Core import face_grab, face_id
from os import mkdir, path, walk
import shutil

# Main window will remain here and the centralWidget will change
class MainWindow(qt.QtWidgets.QMainWindow):
    # Create variables we want to use later, so that they're considered declared in the init
    main_pic_path = None
    names_list = []
    pic_path_dict = {}
    picsorter_path = None
    sample_pic_paths = []
    picsorter_base = None
    returned = False

    def __init__(self, main_app, *args, **kwargs):
        self.main_app = main_app
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Simple Pic Sorter')
        # resize the window to 400x200
        self.resize(400, 200)
        # instantiate our main widget, then set it as the Central widget
        self.path_entry_widget = PathEntryWidget(self)
        self.setCentralWidget(self.path_entry_widget)
        # Load our color theme
        file = qt.QtCore.QFile('Darkeum_teal.qss')
        if not file.open(qt.QtCore.QFile.ReadOnly | qt.QtCore.QFile.Text):
            return
        qss = qt.QtCore.QTextStream(file)
        self.setStyleSheet(qss.readAll())
        # show our window
        self.show()
        # Needed so the x will exit the program
        sys.exit(self.main_app.exec())

    @qt.QtCore.Slot()
    def go(self, *args, **kwargs):
        if not self.returned:
            if not path.exists(self.picsorter_base):
                mkdir(self.picsorter_base)
            sample_pics_path = path.join(self.picsorter_base, 'sample_pics')
            if not path.exists(sample_pics_path):
                mkdir(sample_pics_path)
            new_sample_list = []
            for p in self.sample_pic_paths:
                new_p = path.join(sample_pics_path, path.split(p)[1])
                shutil.copyfile(p, new_p)
                new_sample_list.append(new_p)
            self.sample_pic_paths = new_sample_list.copy()
            train_sets_path = path.join(self.picsorter_base, 'train_sets')
            if not path.exists(train_sets_path):
                mkdir(train_sets_path)
            for name, path_list in self.pic_path_dict.items():
                this_path = path.join(train_sets_path, name)
                if not path.exists(this_path):
                    mkdir(this_path)
                i = 0
                for p in path_list:
                    faces = face_grab.extract_faces(p)
                    for face in faces:
                        face.resize((224, 224)).save(path.join(this_path, f'{name}{i}.jpg'))
                        i += 1
        face_id.main(self.picsorter_base, self.sample_pic_paths)


# This has a layout structure all of our widgets will inherit. This will make things easier on me,
# who would really rather minimize UI coding time (I'm here for the data) XD
class GroupBoxWidget(qt.QtWidgets.QWidget):
    def __init__(self, root, title='Add a title', *args, **kwargs):
        self.root = root
        super().__init__(*args, **kwargs)
        # Set up a grid layout to put our group box in.
        self.layout = qt.QtWidgets.QGridLayout(self)
        # create our group box, adding it to our layout.
        self.gb = qt.GroupBox(self.root, title=title, layout=self.layout)
        # Add a vertical box layout to our group box
        self.gblayout = qt.QtWidgets.QVBoxLayout(self.gb)


class PathEntryWidget(GroupBoxWidget):
    def __init__(self, root, *args, **kwargs):
        super().__init__(root, title='Select Picture Path', *args, **kwargs)
        self.path_label = qt.Label(self.root,
                                   text='Click the button below to select the path where your pictures\n'
                                        'are stored. Note that this process will work best if all the\n'
                                        'pictures you want sorted are in one path.',
                                   layout=self.gblayout)
        self.path_entry = qt.PushButton(self.root,
                                        text='Select Pictures path',
                                        layout=self.gblayout,
                                        func=self.select_pic_path)
        self.nav_btn_layout = qt.QtWidgets.QHBoxLayout()
        self.gblayout.addLayout(self.nav_btn_layout)
        self.returning_btn = qt.PushButton(self.root,
                                           text='I\'m back!',
                                           layout=self.nav_btn_layout,
                                           func=self.go_load_previous)
        self.nav_btn_layout.addSpacing(100)
        self.next_btn = qt.PushButton(self.root,
                                      text='Next',
                                      layout=self.nav_btn_layout,
                                      func=self.go_name_entry)
        self.show()

    @qt.QtCore.Slot()
    def select_pic_path(self, *args, **kwargs):
        self.root.main_pic_path = str(qt.QtWidgets.QFileDialog.getExistingDirectory(self.root,
                                                                                    'Select Main Picture path',
                                                                                    path.expanduser('~')))
        self.root.picsorter_base = path.join(self.root.main_pic_path, f'PicSorter')

    @qt.QtCore.Slot()
    def go_name_entry(self, *args, **kwargs):
        if not self.root.main_pic_path:
            return
        self.close()
        self.deleteLater()
        self.root.name_entry_widget = NameEntryWidget(self.root)
        self.root.setCentralWidget(self.root.name_entry_widget)

    @qt.QtCore.Slot()
    def go_load_previous(self, *args, **kwargs):
        self.close()
        self.deleteLater()
        self.root.load_previous_widget = LoadPreviousWidget(self.root)
        self.root.setCentralWidget(self.root.load_previous_widget)


class NameEntryWidget(GroupBoxWidget):
    def __init__(self, root, *args, **kwargs):
        super().__init__(root, title='Enter Names', *args, **kwargs)
        self.entry_rows = []
        if self.root.names_list:
            self.row_count = len(self.root.names_list)
        else:
            self.row_count = 1
        # A label explaining what to do
        self.label = qt.Label(self.root,
                 text='To begin, enter the names of the people you want to sort\n'
                      'pictures of in the slots below. Add or subtract rows as\n'
                      'needed using the arrow buttons. When you are satisfied,\n'
                      'click Next.',
                 alignment=qt.QtCore.Qt.AlignLeft,
                 layout=self.gblayout)
        # Add a vertical box layout in which to place buttons added by the user. This makes it
        # so adding and subtracting rows is much easier and they align nicely
        self.line_layout = qt.QtWidgets.QVBoxLayout()
        self.gblayout.addLayout(self.line_layout)
        # Create a dictionary of lines. The first one is called main_line and subsequent lines are numbered by
        # which row they are (ie the second line is labeled 2); the additional lines are added in a button function
        # below.
        # The value of each is an instance of our LineEdit widget.
        if not self.root.names_list:
            self.entry_rows.append(qt.LineEdit(self.root,
                                               placeholderText='Enter a name here',
                                               layout=self.line_layout))
        else:
            for name in self.root.names_list:
                self.entry_rows.append(qt.LineEdit(self.root,
                                                   text=f'{name}',
                                                   layout=self.line_layout))
        # Add a horizontal box layout to put our plus and minus buttons side by side in
        self.add_sub_layout = qt.QtWidgets.QHBoxLayout()
        self.gblayout.addLayout(self.add_sub_layout)
        # Add our plus and minus buttons
        self.add_button = qt.PushButton(self.root,
                                        text='+',
                                        layout=self.add_sub_layout,
                                        func=self.add_row)
        self.subtract_button = qt.PushButton(self.root,
                                        text='-',
                                        layout=self.add_sub_layout,
                                        func=self.remove_row)
        # Add our back button and next button
        self.nav_btn_layout = qt.QtWidgets.QHBoxLayout()
        self.gblayout.addLayout(self.nav_btn_layout)
        self.back_button = qt.PushButton(self.root,
                                         text='Back',
                                         layout=self.nav_btn_layout,
                                         func=self.back_to_path_select)
        self.nav_btn_layout.addSpacing(100)
        self.next_button = qt.PushButton(self.root,
                                         text='Next',
                                         layout=self.nav_btn_layout,
                                         func=self.go_photo_select)
        self.show()

    @qt.QtCore.Slot()
    def add_row(self, *args, **kwargs):
        # This function pops when the + button is pressed
        # Add 1 to the row count
        self.row_count += 1
        # Add the LineEdit to the dictionary
        self.entry_rows.append(qt.LineEdit(self.root,
                                           placeholderText='Enter a name here',
                                           layout=self.line_layout))

    @qt.QtCore.Slot()
    def remove_row(self, *args, **kwargs):
        # This function pops when the - button is pressed
        # if the row count is 1, we return, thus ignoring the call to delete because there must be one row.
        if self.row_count == 1:
            return False
        # Make a variable to easily access the instance of the lineedit widget
        wid = self.entry_rows[-1]
        this_name = wid.text()
        # Remove the widget from the layout
        self.line_layout.removeWidget(wid)
        # Mark the widget for deletion
        wid.deleteLater()
        # Delete the line from the dictionary
        del self.entry_rows[-1]
        # remove the name from the names list, if it exists
        try:
            del self.root.names_list[self.root.names_list.index(this_name)]
        except ValueError:
            pass
        # Subtract 1 from the row count (new row count)
        self.row_count -= 1
        # Return true in case we ever need that functionality for some reason
        return True

    @qt.QtCore.Slot()
    def back_to_path_select(self, *args, **kwargs):
        self.get_names()
        self.close()
        self.deleteLater()
        self.root.path_entry_widget = PathEntryWidget(self.root)
        self.root.setCentralWidget(self.root.path_entry_widget)

    @qt.QtCore.Slot()
    def go_photo_select(self, *args, **kwargs):
        # This function pops when the Next button is pressed.
        # If the list is not blank:
        self.get_names()
        if self.root.names_list:
            # close this widget
            self.close()
            self.deleteLater()
            # Instantiate the second widget, making it an attribute of root
            self.root.photo_select_widget = PhotoSelectWidget(self.root)
            # Set the second widget as root's central widget
            self.root.setCentralWidget(self.root.photo_select_widget)

    def get_names(self, *args, **kwargs):
        # reset the list to write in whatever is there now
        self.root.names_list = []
        # For every line in the list:
        for i in range(len(self.entry_rows)):
            # Name will be the text from the lineedit stripped of leading and trailing space
            name = self.entry_rows[i].text().strip()
            # If the name isn't blank, append it to the list
            if name:
                self.root.names_list.append(name)
        

class PhotoSelectWidget(GroupBoxWidget):
    def __init__(self, root, *args, **kwargs):
        super().__init__(root, title='Select Photos', *args, **kwargs)
        # Create dictionary of buttons with labels.
        self.name_btn_dict = {}
        for i,name in enumerate(self.root.names_list):
            self.name_btn_dict[name] = {'btn': qt.PushButton(self.root,
                                                       text=f'{name}',
                                                       layout=self.gblayout,
                                                       func=partial(self.launch_selection, name)),
                                        'label': qt.Label(self.root,
                                                            text=f'{name}\'s pictures will populate here once they have been\n'
                                                                 f'chosen by clicking the button above.',
                                                            layout=self.gblayout)}

        self.nav_btn_layout = qt.QtWidgets.QHBoxLayout()
        self.gblayout.addLayout(self.nav_btn_layout)
        self.back_button = qt.PushButton(self.root,
                                         text='Back',
                                         layout=self.nav_btn_layout,
                                         func=self.back_to_names)
        self.next_button = qt.PushButton(self.root,
                                         text='Next',
                                         layout=self.nav_btn_layout,
                                         func=self.go_sample_photo_select)
        self.show()

    @qt.QtCore.Slot()
    def back_to_names(self, *args, **kwargs):
        self.close()
        self.deleteLater()
        self.root.name_entry_widget = NameEntryWidget(self.root)
        self.root.setCentralWidget(self.root.name_entry_widget)

    @qt.QtCore.Slot()
    def go_sample_photo_select(self, *args, **kwargs):
        for name in self.root.names_list:
            try:
                if not self.root.pic_path_dict[name]:
                    return
            except KeyError:
                return
        self.close()
        self.deleteLater()
        self.root.sample_photo_select = SamplePhotoSelect(self.root)
        self.root.setCentralWidget(self.root.sample_photo_select)

    @qt.QtCore.Slot()
    def launch_selection(self, name, *args, **kwargs):
        dialog = qt.QtWidgets.QFileDialog(self)
        dialog.setDirectory(self.root.main_pic_path)
        dialog.setFileMode(qt.QtWidgets.QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilter("Images (*.png *.jpg *.PNG *.JPG)")
        dialog.setViewMode(qt.QtWidgets.QFileDialog.ViewMode.List)
        if dialog.exec():
            self.root.pic_path_dict[name] = dialog.selectedFiles()


class SamplePhotoSelect(GroupBoxWidget):
    def __init__(self, root, *args, **kwargs):
        super().__init__(root, title='Sample Photo Selection', *args, **kwargs)
        self.pic_label = qt.Label(self.root,
                                  text='Click the button below and select 5-10 sample pictures.\n'
                                       'Ideally, each one will have at least 2 of the people you\n'
                                       'have provided names and pictures of. Between all samples,\n'
                                       'you should try to make sure each person is in at least one.',
                                  layout=self.gblayout)
        self.select_btn = qt.PushButton(self.root,
                                        text='Select Sample Photos',
                                        layout=self.gblayout,
                                        func=self.select_photos)
        self.pic_label = qt.Label(self.root,
                                  text='Thumbnails of your sample pictures will show here once you\n'
                                       'have chosen them by clicking the button above',
                                  layout=self.gblayout)
        self.nav_btn_layout = qt.QtWidgets.QHBoxLayout()
        self.gblayout.addLayout(self.nav_btn_layout)
        self.back_button = qt.PushButton(self.root,
                                         text='Back',
                                         layout=self.nav_btn_layout,
                                         func=self.back_to_photo_select)
        self.nav_btn_layout.addSpacing(100)
        self.next_button = qt.PushButton(self.root,
                                         text='Next',
                                         layout=self.nav_btn_layout,
                                         func=self.go)
        self.show()

    @qt.QtCore.Slot()
    def select_photos(self, *args, **kwargs):
        dialog = qt.QtWidgets.QFileDialog(self)
        dialog.setDirectory(self.root.main_pic_path)
        dialog.setFileMode(qt.QtWidgets.QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilter("Images (*.png *.jpg *.PNG *.JPG *.jpeg *.JPEG)")
        dialog.setViewMode(qt.QtWidgets.QFileDialog.ViewMode.List)
        if dialog.exec():
            self.root.sample_pic_paths = dialog.selectedFiles()

    @qt.QtCore.Slot()
    def go(self, *args, **kwargs):
        if not self.root.sample_pic_paths:
            return
        self.root.go()


    @qt.QtCore.Slot()
    def back_to_photo_select(self, *args, **kwargs):
        self.close()
        self.deleteLater()
        self.root.photo_select_widget = PhotoSelectWidget(self.root)
        self.root.setCentralWidget(self.root.photo_select_widget)


class LoadPreviousWidget(GroupBoxWidget):
    def __init__(self, root, *args, **kwargs):
        super().__init__(root, title='Load Previous Project', *args, **kwargs)
        self.label = qt.Label(self.root,
                              text='Click the button below to select the PicSorter folder that\n'
                                   'was created last time.',
                              layout=self.gblayout)
        self.path_select = qt.PushButton(self.root,
                                         text='Select Picsorter Directory Path',
                                         layout=self.gblayout,
                                         func=self.get_picsorter_folder)
        self.nav_btn_layout = qt.QtWidgets.QHBoxLayout()
        self.gblayout.addLayout(self.nav_btn_layout)
        self.go_back = qt.PushButton(self.root,
                                     text='Back to new',
                                     layout=self.nav_btn_layout,
                                     func=self.back_to_new)
        self.nav_btn_layout.addSpacing(100)
        self.go = qt.PushButton(self.root,
                                text='Go!',
                                layout=self.nav_btn_layout,
                                func=self.go_ahead)

    @qt.QtCore.Slot()
    def get_picsorter_folder(self, *args, **kwargs):
        self.root.picsorter_base = str(qt.QtWidgets.QFileDialog.getExistingDirectory(self.root,
                                                                                     'Select PicSorter Directory path',
                                                                                     path.expanduser('~')))

    @qt.QtCore.Slot()
    def back_to_new(self, *args, **kwargs):
        self.close()
        self.deleteLater()
        self.root.path_entry_widget = PathEntryWidget(self.root)
        self.root.setCentralWidget(self.root.path_entry_widget)

    @qt.QtCore.Slot()
    def go_ahead(self, *args, **kwargs):
        sample_pics_path = path.join(self.root.picsorter_base, 'sample_pics')
        for root, dirs, files, in walk(sample_pics_path):
            self.root.sample_pic_paths = [path.join(sample_pics_path, x) for x in files]
            break
        self.root.returned = True
        self.root.go()
