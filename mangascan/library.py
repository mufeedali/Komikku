from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf

from mangascan.model import create_db_connection
from mangascan.model import Manga


class Library():
    def __init__(self, window):
        self.window = window
        self.builder = window.builder

        self.flowbox = self.builder.get_object('library_page_flowbox')
        self.flowbox.connect('child-activated', self.on_manga_clicked)

        def sort(child1, child2):
            """
            This function gets two children and has to return:
            - a negative integer if the firstone should come before the second one
            - zero if they are equal
            - a positive integer if the second one should come before the firstone
            """
            manga1 = Manga(child1.get_children()[0].manga.id)
            manga2 = Manga(child2.get_children()[0].manga.id)

            if manga1.last_read > manga2.last_read:
                return -1
            elif manga1.last_read < manga2.last_read:
                return 1
            else:
                return 0

        self.flowbox.set_sort_func(sort)

        self.populate()

    def add_manga(self, manga, position=-1):
        overlay = Gtk.Overlay()
        overlay.set_size_request(180, 250)
        overlay.set_halign(Gtk.Align.CENTER)
        overlay.set_valign(Gtk.Align.CENTER)
        overlay.manga = manga

        # Cover
        image = Gtk.Image()
        if manga.cover_fs_path is not None:
            pixbuf = Pixbuf.new_from_file_at_scale(manga.cover_fs_path, 180, -1, True)
        else:
            pixbuf = Pixbuf.new_from_resource_at_scale('/com/gitlab/valos/MangaScan/images/missing_file.png', 180, -1, True)
        image.set_from_pixbuf(pixbuf)
        overlay.add_overlay(image)

        # Name (bottom)
        label = Gtk.Label()
        label.get_style_context().add_class('library-manga-name-label')
        label.set_valign(Gtk.Align.END)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_text(manga.name)
        overlay.add_overlay(label)

        # Server logo (top left corner)
        def draw(da, ctx):
            size = 40

            ctx.save()

            # Draw triangle
            ctx.set_source_rgba(0, 0, 0, .5)
            ctx.new_path()
            ctx.move_to(0, 0)
            ctx.rel_line_to(0, size)
            ctx.rel_line_to(size, -size)
            ctx.close_path()
            ctx.fill()

            # Draw logo
            pixbuf = Pixbuf.new_from_resource_at_scale(
                '/com/gitlab/valos/MangaScan/icons/ui/favicons/{0}.ico'.format(manga.server_id), 16, 16, True)
            Gdk.cairo_set_source_pixbuf(ctx, pixbuf, 2, 2)
            ctx.paint()

            ctx.restore()

        drawingarea = Gtk.DrawingArea()
        drawingarea.connect('draw', draw)
        overlay.add_overlay(drawingarea)

        overlay.show_all()
        self.flowbox.insert(overlay, position)

    def on_manga_added(self, manga):
        """
        Called from 'Add dialog' when user clicks on + button
        """
        db_conn = create_db_connection()
        nb_mangas = db_conn.execute('SELECT count(*) FROM mangas').fetchone()[0]
        db_conn.close()

        if nb_mangas == 1:
            # Library was previously empty
            self.populate()
        else:
            self.add_manga(manga)

    def on_manga_clicked(self, flowbox, child):
        self.window.card.open_manga(child.get_children()[0].manga)

    def on_manga_deleted(self, manga):
        # Remove manga cover in flowbox
        for child in self.flowbox.get_children():
            if child.get_children()[0].manga == manga:
                child.destroy()
                break

    def populate(self):
        db_conn = create_db_connection()
        mangas_rows = db_conn.execute('SELECT * FROM mangas ORDER BY last_read DESC').fetchall()

        if len(mangas_rows) == 0:
            if self.window.overlay.is_ancestor(self.window):
                self.window.remove(self.window.overlay)

            # Display first start message
            self.window.add(self.window.first_start_grid)

            return

        if self.window.first_start_grid.is_ancestor(self.window):
            self.window.remove(self.window.first_start_grid)

        self.window.add(self.window.overlay)

        # Clear library flowbox
        for child in self.flowbox.get_children():
            self.flowbox.remove(child)
            child.destroy()

        # Populate flowbox with mangas covers
        for row in mangas_rows:
            self.add_manga(Manga(row['id']))

        db_conn.close()

        self.flowbox.show_all()

    def show(self):
        self.window.headerbar.set_title('Manga Scan')

        self.builder.get_object('left_button_image').set_from_icon_name('list-add-symbolic', Gtk.IconSize.MENU)

        self.builder.get_object('menubutton').set_menu_model(self.builder.get_object('menu'))
        self.builder.get_object('menubutton_image').set_from_icon_name('open-menu-symbolic', Gtk.IconSize.MENU)

        self.flowbox.invalidate_sort()
        self.window.show_page('library')
