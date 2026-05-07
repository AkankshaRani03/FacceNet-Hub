from utils.recognition import recognize_face_safe


def verify_faces(img1_path, img2_path, threshold=0.35):
    """Simple 1:1 verification using classification model output."""
    r1 = recognize_face_safe(img1_path, threshold=threshold)
    r2 = recognize_face_safe(img2_path, threshold=threshold)

    id1 = r1.get('id') or 'UNKNOWN'
    id2 = r2.get('id') or 'UNKNOWN'
    conf1 = float(r1.get('confidence') or 0.0)
    conf2 = float(r2.get('confidence') or 0.0)

    if id1 == 'UNKNOWN' or id2 == 'UNKNOWN':
        return {
            'same': False,
            'message': 'At least one face is not recognized',
            'id1': id1,
            'id2': id2,
            'confidence1': conf1,
            'confidence2': conf2
        }

    same = id1 == id2
    return {
        'same': same,
        'message': 'Same Person' if same else 'Different Persons',
        'id1': id1,
        'id2': id2,
        'confidence1': conf1,
        'confidence2': conf2
    }

        