import numpy as np
import cv2 as cv
import os
from processes import ProcessWrapper
from opencv.cv_udp_video_receiver import CvUdpVideoReceiver
from tuio.tuio_receiver import TuioReceiver
from tuio.tuio_sender import TuioSender
from tuio.tuio_elements import TuioPointer, TuioData, TuioElement
from webutils import api_helper


class SurfaceReceiver(ProcessWrapper):
    def __init__(self, frame_port, tuio_port, server_ip, width=640, height=480, ip="0.0.0.0",
                 video_protocol="jpeg", download_folder="CLIENT_DATA/", user_id=-1):
        super().__init__()
        self._frame_port = frame_port
        self._tuio_port = tuio_port
        self._server_ip = server_ip
        self._ip = ip
        self._width = width
        self._height = height
        self._video_protocol = video_protocol
        self._download_folder = download_folder
        self._user_id = user_id
        self._compute_launch_command()

    def _compute_launch_command(self):
        args = []
        args.append("python3")
        args.append(os.path.abspath(__file__))
        args.append("-frame_port")
        args.append(str(self._frame_port))
        args.append("-tuio_port")
        args.append(str(self._tuio_port))
        args.append("-server_ip")
        args.append(str(self._server_ip))
        args.append("-ip")
        args.append(str(self._ip))
        args.append("-video_protocol")
        args.append(str(self._video_protocol))
        args.append("-width")
        args.append(str(self._width))
        args.append("-height")
        args.append(str(self._height))
        args.append("-download_folder")
        args.append(str(self._download_folder))
        args.append("-user_id")
        args.append(str(self._user_id))
        self._set_process_args(args)

    def set_port(self, port):
        self._frame_port = port
        self._compute_launch_command()

    def set_protocol(self, protocol):
        self._video_protocol = protocol
        self._compute_launch_command()


def parse_color_bgr(elmt: TuioElement):
    clr_data = elmt.get_value_by_mime_type("rgb")
    clr = (0, 255, 0)  # default
    if clr_data is not None:
        rgb = TuioData.parse_str_to_rgb(clr_data)
        if len(rgb) == 3:
            clr = (rgb[2], rgb[1], rgb[0])
    return clr


if __name__ == "__main__":
    import sys

    user_colors = []
    for r in [0, 255]:
        for g in [0, 255]:
            for b in [0, 255]:
                user_colors.append((b, g, r))

    # Parse args
    IP = "0.0.0.0"
    FRAME_PORT = 5002
    TUIO_PORT = 5003
    PROTOCOL = "jpeg"
    DOWNLOAD_FOLDER = "CLIENT_DATA/"
    W = 640
    H = 480
    WINDOW_NAME = "SurfaceStreams Receiver"
    POINTER_RADIUS = 10
    USER_ID = -1
    if len(sys.argv) > 1:
        arg_i = 1
        while arg_i < len(sys.argv):
            arg = sys.argv[arg_i]
            if arg == "-frame_port":
                arg_i += 1
                FRAME_PORT = int(sys.argv[arg_i])
            elif arg == "-tuio_port":
                arg_i += 1
                TUIO_PORT = int(sys.argv[arg_i])
            elif arg == "-video_protocol":
                arg_i += 1
                PROTOCOL = sys.argv[arg_i]
            elif arg == "-ip":
                arg_i += 1
                IP = sys.argv[arg_i]
            elif arg == "-server_ip":
                arg_i += 1
                api_helper.SERVER_IP = sys.argv[arg_i]
            elif arg == "-w":
                arg_i += 1
                W = int(sys.argv[arg_i])
            elif arg == "-h":
                arg_i += 1
                H = int(sys.argv[arg_i])
            elif arg == "-download_folder":
                arg_i += 1
                DOWNLOAD_FOLDER = sys.argv[arg_i]
            elif arg == "-user_id":
                arg_i += 1
                USER_ID = int(sys.argv[arg_i])
            arg_i += 1

    # TUIO based pattern receiver
    tuio_server = TuioReceiver(ip=IP, port=TUIO_PORT, element_timeout=1.0)
    tuio_server.start()

    # Gst & OpenCV based video stream receiver
    cap = CvUdpVideoReceiver(port=FRAME_PORT, protocol=PROTOCOL)

    # mouse handler for drawing
    ptr = None
    ptr_point = None
    tuio_sender = TuioSender(api_helper.SERVER_IP, api_helper.SERVER_TUIO_PORT)
    user_rgb = [c for c in reversed(user_colors[USER_ID % len(user_colors)])]
    user_rgb_dat = TuioData("rgb", TuioData.parse_rgb_to_str(user_rgb))

    def tuio_cursor_doodle(event, x, y, flags, param):
        global ptr, ptr_point, tuio_sender, USER_ID, user_rgb_dat
        x_scaled = x/float(W)
        y_scaled = y/float(H)

        # check draw
        if event == cv.EVENT_LBUTTONDOWN and ptr is None:
            ptr = TuioPointer(x_pos=x_scaled, y_pos=y_scaled,
                              tu_id=TuioPointer.tu_id_pen, c_id=-2, u_id=USER_ID)
            ptr.append_data(user_rgb_dat)
            ptr_point = None
        elif event == cv.EVENT_MOUSEMOVE and ptr is None:
            if ptr_point is None:
                ptr_point = TuioPointer(x_pos=x_scaled, y_pos=y_scaled,
                                        tu_id=TuioPointer.tu_id_pointer, c_id=-2, u_id=USER_ID)
                ptr_point.append_data(user_rgb_dat)
            ptr_point.x_pos = x_scaled
            ptr_point.y_pos = y_scaled
            tuio_sender.send_pointer(ptr_point)
        elif event == cv.EVENT_LBUTTONUP:
            ptr = None

        # check erase
        if event == cv.EVENT_RBUTTONDOWN and ptr is None:
            ptr = TuioPointer(x_pos=x_scaled, y_pos=y_scaled,
                              tu_id=TuioPointer.tu_id_eraser, c_id=-2, u_id=USER_ID)
            ptr_point = None
        elif event == cv.EVENT_RBUTTONUP:
            ptr = None

        if ptr is not None:
            ptr.x_pos = x_scaled
            ptr.y_pos = y_scaled
            tuio_sender.send_pointer(ptr)

    cv.namedWindow(WINDOW_NAME, cv.WINDOW_NORMAL)
    cv.setMouseCallback(WINDOW_NAME, tuio_cursor_doodle)

    # additional resource init
    images = {}
    img_paths = []

    frame = None
    if cap is None:
        frame = np.zeros((H, W, 3), np.uint8)

    path_frame = None
    point_frame = None
    draw_paths = {}
    draw_points = {}
    erase_paths = {}

    no_capture = False
    while cap.is_capturing():
        update_log = tuio_server.update_elements()

        if no_capture:
            frame[:, :] = (0, 0, 0)
        elif cap is not None:
            # get capture frame and resize to window size
            frame = cap.capture()
            x, y , w, h = cv.getWindowImageRect(WINDOW_NAME)
            H, W, c = frame.shape
            if w > 0 and h > 0:
                frame = cv.resize(frame, (int(w), int(H * (w / W))))
                H, W, c = frame.shape

        # create drawing frames if necessary
        if path_frame is None:
            path_frame = np.zeros((H, W, 3), np.uint8)
        if point_frame is None:
            point_frame = np.zeros((H, W, 3), np.uint8)

        # resize drawing frames if necessary
        H, W, c = frame.shape
        pH, pW, pc = path_frame.shape
        if pH != H or pW != W:
            path_frame = cv.resize(path_frame, (W, H))
        ptH, ptW, ptc = point_frame.shape
        if ptH != H or ptW != W:
            point_frame = cv.resize(point_frame, (W, H))
        else:
            point_frame[:, :] = (0, 0, 0)

        # iterate over all tracked patterns
        for p in tuio_server.get_patterns().values():
            # check next pattern if pattern data not valid
            # can happen if SYM or BND for pattern hasn't been send/received
            if not p.is_valid(): #or (p.get_u_id() != -1 and p.get_u_id() == USER_ID):
                continue
            uuid = p.get_sym().uuid
            # download image if hasn't been downloaded
            if uuid not in images:
                img_path = api_helper.download_image(uuid, DOWNLOAD_FOLDER)
                if len(img_path) > 0:
                    img_paths.append(img_path)
                    images[uuid] = cv.imread(img_path, -1)
            # draw frame around tracked box
            bnd_s = p.get_bnd().scaled(H, H)
            box = cv.boxPoints((
                (bnd_s.x_pos, bnd_s.y_pos),
                (-bnd_s.width, bnd_s.height),
                bnd_s.angle  # bnd_s.angle if bnd_s.width < bnd_s.height else bnd_s.angle - 90
            ))
            clr = user_colors[p.get_u_id() % len(user_colors)]
            frame = cv.polylines(frame, [np.int32(box)], True, clr, 3, cv.LINE_AA)
            # draw transformed pattern onto frame
            if uuid in images:
                # transform pattern
                img = images[uuid].copy()
                img_h, img_w, img_c = img.shape
                pts = np.float32([[0, 0], [0, img_h - 1], [img_w - 1, img_h - 1], [img_w - 1, 0]]).reshape(-1, 1, 2)
                M = cv.getPerspectiveTransform(pts, box)  # order_points(box))
                frame = cv.warpPerspective(img, M, (W, H), frame, borderMode=cv.BORDER_TRANSPARENT)

        draw_points = {}

        pointers = tuio_server.get_pointers()

        # iterate over all tracked pointers
        for p in pointers.values():
            # check next pointer if no data in current
            if p.is_empty():
                continue
            # scale position
            x = int(p.x_pos * W)
            y = int(p.y_pos * H)
            # extend drawing paths
            if p.tu_id == TuioPointer.tu_id_pen:
                if p.key() not in update_log["ptr"]:
                    continue
                if p.key() not in draw_paths:
                    draw_paths[p.key()] = []
                draw_paths[p.key()].append([x, y])
            # extend eraser paths
            elif p.tu_id == TuioPointer.tu_id_eraser:
                if p.key() not in update_log["ptr"]:
                    continue
                if p.key() not in erase_paths:
                    erase_paths[p.key()] = []
                erase_paths[p.key()].append([x, y])
            # extend drawing points
            elif p.tu_id == TuioPointer.tu_id_pointer:
                draw_points[p.key()] = (x, y)

        # draw gathered paths
        for ptr_key, path in draw_paths.items():
            if len(path) <= 1:
                continue
            draw_path = np.array([p for p in path], np.int32)
            draw_paths[ptr_key] = [path[-1]]
            cv.polylines(
                path_frame, [draw_path], False, parse_color_bgr(pointers[ptr_key]),
                int(pointers[ptr_key].radius*2.0)
            )
        # draw gathered erasers
        np_erase_paths = []
        for ptr_key, path in erase_paths.items():
            if len(path) <= 1:
                continue
            np_erase_paths.append(np.array([p for p in path], np.int32))
            erase_paths[ptr_key] = [path[-1]]
        if len(np_erase_paths) > 0:
            cv.polylines(
                path_frame, np_erase_paths, False, (0, 0, 0),
                int(pointers[ptr_key].radius*2.0)
            )
        # draw gathered points
        for ptr_key, point in draw_points.items():
            cv.circle(
                point_frame, point, int(pointers[ptr_key].radius),
                parse_color_bgr(pointers[ptr_key]), -1
            )

        # overlay point and path frames on current frame
        if frame.shape == point_frame.shape:
            frame = cv.add(frame, point_frame)
        if frame.shape == path_frame.shape:
            frame = cv.add(frame, path_frame)

        # overlay user color in top left corner
        frame = cv.rectangle(frame, (10, 10), (40, 40), user_colors[USER_ID % len(user_colors)], cv.FILLED)

        # show current frame
        cv.imshow(WINDOW_NAME, frame)

        # handle keys
        key_pressed = cv.waitKey(1) & 0xFF
        if key_pressed == ord('q'):
            break
        elif key_pressed == ord('n'):
            no_capture = not no_capture
            if no_capture:
                frame = np.zeros((H, W, 3), np.uint8)

    # cleanup
    cap.release()
    cv.destroyAllWindows()
    tuio_server.terminate()
    # remove temp images
    while len(img_paths) > 0:
        img_path = img_paths[0]
        if os.path.exists(img_path):
            os.remove(img_path)
        img_paths.remove(img_path)
