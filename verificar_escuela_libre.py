"""Comprueba escuelas libres y el texto enviado a la plantilla, sin abrir Word."""
from motor import MODOS_PERIODO, TIPOS, validar


def caso(escuela):
    return dict(
        tipo=TIPOS[2], escuela=escuela, folios='2',
        fecha='16/10/2026', entidad='Entidad de Prueba', medico='Dra. Médica de Prueba',
        tratamiento='al estudiante', nombre='Estudiante Ficticio de Prueba',
        codigo='2000001', diagnostico='Diagnóstico ficticio',
        inicio='01/10/2026', fin='15/10/2026', modo_periodo=MODOS_PERIODO[0],
    )


def run():
    accepted = {
        'Escuela de Biología': 'ESCUELA DE BIOLOGÍA',
        'Biología': 'BIOLOGÍA',
        'Escuela de Salud Pública': 'ESCUELA DE SALUD PÚBLICA',
        'E. Ing. Sistemas': 'E. ING. SISTEMAS',
        '  EISI  ': 'EISI',
        'A' * 160: 'A' * 160,
    }
    for entered, expected in accepted.items():
        assert validar(caso(entered))['escuela'] == expected, repr(entered)

    invalid = [
        '', '   ', 'A' * 161, '{{escuela}}', 'Escuela }}',
        'Escuela\nOtra', 'Escuela\rOtra', 'Escuela\tOtra', '\nEscuela',
        'Escuela\n', 'Escuela\x00', 'Escuela\x7f', 'Escuela\x85',
        'Escuela\u2028Otra', 'Escuela\u2029Otra',
    ]
    for entered in invalid:
        try:
            validar(caso(entered))
        except ValueError:
            pass
        else:
            raise AssertionError('Escuela inválida aceptada: ' + repr(entered))

    # Un campo no impreso en certificados no limita esos formatos.
    certificate = caso('A' * 161)
    certificate.update(tipo=TIPOS[0], accion='fue valorado en', especialidad='Medicina General',
                       medico_general='Dr. Médico de Prueba', registro='0000')
    assert 'escuela' not in validar(certificate)
    return {'aceptadas': len(accepted), 'rechazadas': len(invalid), 'certificado_sin_escuela_impresa': True}


if __name__ == '__main__':
    print('OK: escuela libre, abreviaturas, prefijo literal y límites:', run())
