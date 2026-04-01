"""
Management command to seed contract templates (PlantillaContrato).
Creates 9 templates based on real Peruvian labor contracts (DL 728 / DS 003-97-TR).
Usage: python manage.py seed_plantillas_contrato [--force]
"""
from django.core.management.base import BaseCommand
from personal.models import PlantillaContrato


# ═══════════════════════════════════════════════════════════════════════════
# PLANTILLA 1: CONTRATO POR OBRA — PERSONAL DE CONFIANZA
# ═══════════════════════════════════════════════════════════════════════════
CONTRATO_CONFIANZA = """
<h2 style="text-align:center; color:#0f766e;">CONTRATO DE TRABAJO SUJETO A MODALIDAD POR OBRA DETERMINADA</h2>

<p>Conste por el presente documento, que se extiende por duplicado, el <strong>CONTRATO DE TRABAJO SUJETO A MODALIDAD POR OBRA DETERMINADA</strong>, que celebran de una parte, <strong>{{empresa}}</strong> con RUC N.&deg; {{ruc_empresa}} y domicilio fiscal en {{direccion_empresa}}, debidamente representada por su apoderado(a) {{representante_legal}}, identificado(a) con {{tipo_doc_representante}} N.&deg; {{nro_doc_representante}}, a quien en adelante se le denominará <strong>EL EMPLEADOR</strong>, y de la otra parte, <strong>{{nombre_empleado}}</strong> con {{tipo_doc_trabajador}} N.&deg; {{dni}}, domiciliado en {{domicilio}}, a quien en adelante se le denominará <strong>EL TRABAJADOR</strong>, en los términos y condiciones siguientes:</p>

<h4>PRIMERA: ANTECEDENTES</h4>
<p>EL EMPLEADOR es un consorcio constituido en el Perú mediante un contrato de colaboración empresarial, regulada por la Ley General de Sociedades, cuyo objeto es la prestación de servicios de estudios e investigaciones entre otras actividades; la misma que actualmente tiene la necesidad de contratar a un personal idóneo que se desempeñe en el cargo de <strong>{{cargo}}</strong>.</p>
<p>EL TRABAJADOR declara ser un profesional calificado, que cuenta con la experiencia necesaria en el área referida y reconoce ser competente para ocupar el cargo ofrecido.</p>

<h4>SEGUNDA: DE LAS NECESIDADES DE LA CONTRATACIÓN TEMPORAL</h4>
<p>En el ejercicio ordinario de sus actividades, EL EMPLEADOR ha suscrito un contrato de ejecución de servicios con {{obra_cliente}} para la construcción de la obra denominada «{{obra_nombre}}», en adelante LA OBRA.</p>
<p>Con ocasión de la ejecución de estas actividades, EL EMPLEADOR requiere contar con los servicios de personal debidamente capacitado y especializado para que se dedique al desempeño de determinadas ocupaciones y tareas que tienen una fecha de inicio y una fecha de término al tratarse de un proyecto de obra como se indica en este contrato.</p>
<p>Por tal motivo el presente contrato a plazo determinado se encuentra sujeto a la modalidad de Obra Determinada, prevista en el artículo 63.&deg; del Texto Único Ordenado del Decreto Legislativo 728, Ley de Productividad y Competitividad Laboral, aprobado por Decreto Supremo 003-97-TR.</p>

<h4>TERCERA: DE LOS SERVICIOS</h4>
<p>Por el presente contrato, EL TRABAJADOR se obliga a prestar sus servicios a EL EMPLEADOR para realizar actividades inherentes, afines, conexas y complementarias al puesto de <strong>{{cargo}}</strong>, dentro de las cuales se encuentran:</p>
{{funciones_cargo}}
<p>Otras conexas y complementarias al servicio contratado, siendo las tareas y funciones determinadas para EL TRABAJADOR abiertas a la prestación de sus servicios personales en el ámbito de su cargo, no limitándose o circunscribiéndose su labor exclusivamente a las antes referidas, reservándose EL EMPLEADOR el derecho de modificar tales funciones y tareas en relación a las necesidades del servicio y dentro de criterios de razonabilidad.</p>
<p>EL TRABAJADOR no podrá ejercer actividad adicional alguna a las antes expuestas de carácter laboral, profesional o comercial, independientemente que sean remuneradas o no, salvo autorización previa y por escrito de EL EMPLEADOR.</p>

<h4>CUARTA: CALIFICACIÓN COMO PERSONAL DE CONFIANZA</h4>
<p>El puesto de <strong>{{cargo}}</strong> que ocupará EL TRABAJADOR, ha sido calificado por EL EMPLEADOR como puesto de <strong>PERSONAL DE CONFIANZA</strong> por la naturaleza de las labores asignadas. EL TRABAJADOR en el ejercicio de sus funciones tendrá acceso a información confidencial y reservada de EL EMPLEADOR, vinculada a las actividades propias de esta.</p>
<p>Asimismo, por la naturaleza de su cargo y funciones EL TRABAJADOR laborará en contacto personal y directo con EL EMPLEADOR o con el personal de dirección; por lo que, de conformidad con lo previsto por el artículo 43.&deg; del Texto Único Ordenado del Decreto Legislativo N.&deg; 728, aprobada mediante D.S. N.&deg; 003-97-TR, EL EMPLEADOR califica a EL TRABAJADOR como personal de confianza. Por su parte, EL TRABAJADOR acepta esta calificación.</p>

<h4>QUINTA: SOBRE LA NOTIFICACIÓN DE DESCARGOS Y SANCIONES</h4>
<p>EL TRABAJADOR señala su total conformidad de que se le remita o notifique cualquier tipo de comunicación referente a memorándums, amonestaciones, sanciones y cualquier otro tema en general al correo electrónico {{email_trabajador}}, teniendo las comunicaciones remitidas los mismos efectos que una carta notarial.</p>

<h4>SEXTA: ENTREGA ELECTRÓNICA DE DOCUMENTOS LABORALES</h4>
<p>Conforme a lo dispuesto en el numeral 3.2 del artículo 3 del Decreto Legislativo N.&deg; 1310, EL TRABAJADOR señala su total conformidad de que se le remita documentos de índole laboral como boletas de pago, altas, baja, liquidación de beneficios sociales al correo electrónico {{email_trabajador}}.</p>

<h4>SÉPTIMA: TRASLADOS</h4>
<p>Ambas partes acuerdan que EL EMPLEADOR tendrá la facultad de disponer la realización de las labores en cualquiera de sus centros de trabajo, incluso fuera de Lima. EL TRABAJADOR manifiesta que está dispuesto a desplazarse a cualquier punto de la República del Perú donde su presencia sea necesaria.</p>

<h4>OCTAVA: PREVENCIÓN DEL LAVADO DE ACTIVOS Y DELITO DE COHECHO</h4>
<p>EL TRABAJADOR declara conocer y aceptar el Modelo de Prevención de Delitos (MPD) que implementa EL EMPLEADOR, conforme a la Ley N.&deg; 30424. EL TRABAJADOR se compromete a actuar en respeto de los principios y valores fundamentales de EL EMPLEADOR.</p>

<h4>NOVENA: DEL LUGAR DE TRABAJO</h4>
<p>EL TRABAJADOR laborará principalmente en el centro de trabajo donde se desarrolla LA OBRA, o aquel designado por EL EMPLEADOR. Es condición indispensable que EL TRABAJADOR tenga disponibilidad de realizar labores en cualquier lugar.</p>

<h4>DÉCIMA: JORNADA Y HORARIO DE TRABAJO</h4>
<p>Tratándose de un cargo no sujeto a fiscalización, de conformidad con lo previsto en el artículo 11.&deg; del Decreto Supremo N.&deg; 008-2002-TR, Reglamento de la Ley de Jornada de Trabajo, T.U.O del Decreto Legislativo N.&deg; 854, EL TRABAJADOR no se encuentra sujeto a la jornada laboral establecida por EL EMPLEADOR.</p>
<p>En razón a lo expuesto, EL TRABAJADOR no será merecedor al pago de trabajo en sobretiempo u horas extras. EL TRABAJADOR goza de la facultad de organizar discrecionalmente su tiempo de trabajo y queda liberado de la obligación de registrar su asistencia diaria.</p>

<h4>DÉCIMA PRIMERA: DE LA REMUNERACIÓN</h4>
<p>EL EMPLEADOR abonará a EL TRABAJADOR una remuneración bruta mensual ascendente a <strong>{{remuneracion}}</strong> ({{remuneracion_letras}}), de la cual se deducirán los descuentos, aportaciones, retenciones de ley y demás que resulten aplicables.</p>
<p>Adicionalmente, de acuerdo con la legislación laboral peruana vigente, tiene derecho al pago de dos (2) gratificaciones legales y la Compensación por Tiempo de Servicios (CTS) con arreglo a Ley.</p>

<h4>DÉCIMA SEGUNDA: DEL RÉGIMEN LABORAL</h4>
<p>EL TRABAJADOR se encuentra sujeto al Régimen Laboral de la Actividad Privada y le son aplicables los derechos y beneficios previstos en el mismo.</p>

<h4>DÉCIMA TERCERA: VIGENCIA Y PERÍODO DE PRUEBA</h4>
<p>El presente contrato se pacta por un plazo desde el <strong>{{fecha_inicio}}</strong> hasta el <strong>{{fecha_fin}}</strong>, concluyendo a su vencimiento o en la fecha de culminación del servicio, lo que suceda primero.</p>
<p>El plazo se pacta al amparo del artículo 63.&deg; de la LPCL, aprobado por D.S. N.&deg; 003-97-TR.</p>
<p>Atendiendo a la naturaleza del cargo de confianza, las partes acuerdan un período de prueba de <strong>{{periodo_prueba}}</strong> contados desde el inicio de la prestación del servicio, en virtud del artículo 10.&deg; del D.Leg. N.&deg; 728.</p>

<h4>DÉCIMA CUARTA: BUENA FE, EXCLUSIVIDAD Y CONFIDENCIALIDAD</h4>
<p>EL TRABAJADOR se obliga a poner al servicio de EL EMPLEADOR toda su capacidad, diligencia, esmero y lealtad. Asimismo, se compromete a guardar reserva de toda información confidencial. Esta obligación subsistirá aún después de terminada la relación laboral.</p>

<h4>DÉCIMA QUINTA: PROPIEDAD INDUSTRIAL E INTELECTUAL</h4>
<p>Todos los proyectos científicos y tecnológicos generados en virtud de la relación laboral serán propiedad de EL EMPLEADOR.</p>

<h4>DÉCIMA SEXTA: CONFLICTO DE INTERESES</h4>
<p>EL TRABAJADOR declara no compartir ningún tipo de interés con proveedores o terceros que mantengan relaciones con EL EMPLEADOR. Se compromete a desempeñar sus funciones con objetividad e independencia.</p>

<h4>DÉCIMA SÉPTIMA: ENTREGA DE MATERIALES Y RESPONSABILIDAD POR DAÑOS</h4>
<p>EL TRABAJADOR se obliga a cuidar y mantener en buen estado todos los bienes, herramientas y equipos proporcionados por EL EMPLEADOR.</p>

<h4>DÉCIMA OCTAVA: USO DEL CORREO ELECTRÓNICO</h4>
<p>El servicio de correo electrónico y equipos proporcionados por EL EMPLEADOR son para uso exclusivo de fines laborales.</p>

<h4>DÉCIMA NOVENA: EXÁMENES MÉDICOS</h4>
<p>EL TRABAJADOR se someterá a los exámenes médicos programados por EL EMPLEADOR de acuerdo con la Ley N.&deg; 29783.</p>

<h4>VIGÉSIMA: PROTECCIÓN DE DATOS PERSONALES</h4>
<p>EL TRABAJADOR autoriza a EL EMPLEADOR a realizar tratamiento de sus datos personales para la ejecución de la relación contractual.</p>

<h4>VIGÉSIMA PRIMERA: SEGURIDAD Y SALUD EN EL TRABAJO</h4>
<p>Conforme a la Ley N.&deg; 29783, EL EMPLEADOR informa las recomendaciones de seguridad aplicables al cargo de {{cargo}}. EL TRABAJADOR se obliga a cumplir con las normas de seguridad y salud en el trabajo.</p>

<h4>VIGÉSIMA SEGUNDA: EXPOSICIÓN A RIESGOS</h4>
<p>EL EMPLEADOR pone en conocimiento de EL TRABAJADOR los riesgos laborales aplicables: riesgos disergonómicos, caídas, golpes, riesgos eléctricos y oftalmológicos.</p>

<h4>VIGÉSIMA TERCERA: USO DE ALCOHOLÍMETRO</h4>
<p>EL TRABAJADOR reconoce la necesidad del uso del alcoholímetro y acepta ser sometido a esta modalidad de despistaje de acuerdo con las políticas de EL EMPLEADOR.</p>

<h4>VIGÉSIMA CUARTA: COMPETENCIA JURISDICCIONAL Y DOMICILIOS</h4>
<p>Las partes se someten a la competencia jurisdiccional de los Juzgados Especializados de Trabajo de la Ciudad de Lima.</p>

<p style="margin-top:25px;">Hecho y firmado en dos (02) ejemplares de un mismo tenor por EL TRABAJADOR y por EL EMPLEADOR, el día {{fecha_firma}}, en la ciudad de {{ciudad_firma}}, Perú, en señal de entera conformidad.</p>
"""

# ═══════════════════════════════════════════════════════════════════════════
# PLANTILLA 2: CONTRATO POR OBRA — PERSONAL FISCALIZABLE
# ═══════════════════════════════════════════════════════════════════════════
CONTRATO_FISCALIZABLE = """
<h2 style="text-align:center; color:#0f766e;">CONTRATO DE TRABAJO SUJETO A MODALIDAD POR OBRA DETERMINADA</h2>

<p>Conste por el presente documento, que se extiende por duplicado, el <strong>CONTRATO INDIVIDUAL DE TRABAJO SUJETO A MODALIDAD POR OBRA DETERMINADA</strong> celebrado de conformidad con el Artículo 63.&deg; del Decreto Supremo N.&deg; 003-97-TR, de una parte, <strong>{{empresa}}</strong> identificado con RUC N.&deg; {{ruc_empresa}}, con domicilio fiscal en {{direccion_empresa}}, debidamente representada por su apoderado(a) {{representante_legal}} identificado(a) con {{tipo_doc_representante}} {{nro_doc_representante}}, a quien en adelante se le denominará <strong>EL EMPLEADOR</strong>, y de la otra parte <strong>{{nombre_empleado}}</strong> con {{tipo_doc_trabajador}} {{dni}} domiciliado en {{domicilio}}, con correo electrónico {{email_trabajador}}; a quien en adelante se le denominará <strong>EL TRABAJADOR</strong>, en los términos y condiciones siguientes:</p>

<h4>PRIMERA: ANTECEDENTES</h4>
<p>EL EMPLEADOR es un consorcio constituido en el Perú mediante un contrato de colaboración empresarial, que requiere contratar personal a plazo determinado con el cargo <strong>{{cargo}}</strong>.</p>
<p>EL TRABAJADOR es una persona que manifiesta estar calificado para la prestación de los servicios que requiere EL EMPLEADOR.</p>

<h4>SEGUNDA: OBJETO</h4>
<p>En el ejercicio ordinario de sus actividades, EL EMPLEADOR suscribió con {{obra_cliente}} el Acuerdo Contractual para la ejecución de la obra denominada «{{obra_nombre}}», en adelante LA OBRA.</p>
<p>Con ocasión de la ejecución de estas actividades, EL EMPLEADOR requiere contar con los servicios de personal debidamente capacitado. Por tal motivo el presente contrato se sujeta a la modalidad de Obra Determinada, prevista en el artículo 63.&deg; del T.U.O. del Decreto Legislativo N.&deg; 728, aprobado por Decreto Supremo N.&deg; 003-97-TR.</p>
<p>Las funciones que EL TRABAJADOR desarrollará en calidad de <strong>{{cargo}}</strong> para la ejecución de LA OBRA, son entre otras tareas afines, conexas y complementarias, las siguientes:</p>
{{funciones_cargo}}
<p>Otras conexas y complementarias al servicio contratado, reservándose EL EMPLEADOR el derecho de modificar tales funciones dentro de criterios de razonabilidad.</p>

<h4>TERCERA: CALIFICACIÓN COMO PERSONAL ORDINARIO</h4>
<p>El puesto de <strong>{{cargo}}</strong> que ocupará EL TRABAJADOR, ha sido calificado por EL EMPLEADOR como puesto de <strong>personal ordinario</strong>, por la naturaleza de las labores asignadas, debido a que EL TRABAJADOR:</p>
<ol>
<li>No comparte funciones de control y/o administración cuya actividad y grado de responsabilidad depende el resultado de la actividad empresarial.</li>
<li>No tiene acceso a secretos industriales, comerciales o profesionales.</li>
<li>No tiene acceso a información de carácter reservado.</li>
</ol>

<h4>CUARTA: LUGAR DE TRABAJO</h4>
<p>EL TRABAJADOR laborará en el domicilio designado por EL EMPLEADOR o donde EL EMPLEADOR lo determine de acuerdo a las necesidades del proyecto.</p>

<h4>QUINTA: JORNADA LABORAL Y HORARIO DE TRABAJO</h4>
<p>La jornada de trabajo aplicable a EL TRABAJADOR tendrá una extensión de <strong>8 horas diarias o {{jornada_semanal}} semanales</strong>.</p>
<p>La jornada de trabajo será de lunes a viernes establecido en obra, de acuerdo al horario que rige en EL EMPLEADOR, considerando una (1) hora de refrigerio.</p>
<p>Conforme al artículo 7.&deg; del Decreto Supremo N.&deg; 007-2002-TR, el tiempo de refrigerio no forma parte de la jornada ni del horario de trabajo.</p>
<p>EL TRABAJADOR se encontrará sujeto a un control efectivo de su tiempo de trabajo y se encuentra obligado a registrar sus ingresos y salidas en el Registro de Control de Tiempos implementado por EL EMPLEADOR.</p>

<h4>SEXTA: REMUNERACIÓN</h4>
<p>EL EMPLEADOR abonará a EL TRABAJADOR una remuneración bruta mensual ascendente a <strong>{{remuneracion}}</strong> ({{remuneracion_letras}}), de la cual se deducirán los descuentos, aportaciones, retenciones de ley y demás que resulten aplicables.</p>
<p>Adicionalmente, tendrá derecho al pago de las dos (2) gratificaciones legales y la Compensación por Tiempo de Servicios (CTS) con arreglo a Ley.</p>

<h4>SÉPTIMA: RÉGIMEN LABORAL</h4>
<p>EL TRABAJADOR se encuentra sujeto al Régimen Laboral Común de la Actividad Privada y le son aplicables los derechos y beneficios previstos en el mismo.</p>

<h4>OCTAVA: DURACIÓN</h4>
<p>El plazo de duración del presente contrato rige a partir del <strong>{{fecha_inicio}}</strong> hasta el <strong>{{fecha_fin}}</strong>, fecha en que terminará el contrato.</p>
<p>El plazo se pacta al amparo del Artículo 63.&deg; de la LPCL, aprobado por Decreto Supremo N.&deg; 003-97-TR, hasta alcanzar el máximo legal de cinco (5) años establecido por el artículo 74.&deg; de la LPCL.</p>
<p>La suspensión del contrato por alguna de las causas previstas en el artículo 12.&deg; de la LPCL no interrumpirá el plazo de duración.</p>

<h4>NOVENA: PERÍODO DE PRUEBA</h4>
<p>Las partes acuerdan un período de prueba de <strong>{{periodo_prueba}}</strong> de acuerdo con lo que establece el artículo 10.&deg; de la LPCL, a cuyo término el trabajador tendrá derecho a la protección contra el despido arbitrario.</p>

<h4>DÉCIMA: NOTIFICACIÓN DE DESCARGOS Y SANCIONES</h4>
<p>EL TRABAJADOR señala su total conformidad de que se le notifique cualquier comunicación al correo electrónico {{email_trabajador}}, con los mismos efectos que una carta notarial.</p>

<h4>DÉCIMA PRIMERA: ENTREGA ELECTRÓNICA DE DOCUMENTOS LABORALES</h4>
<p>Conforme al Decreto Legislativo N.&deg; 1310, EL TRABAJADOR acepta la remisión electrónica de documentos laborales (boletas, altas, liquidaciones) al correo electrónico {{email_trabajador}}.</p>

<h4>DÉCIMA SEGUNDA: TRASLADOS</h4>
<p>EL EMPLEADOR tendrá la facultad de disponer la realización de las labores en cualquiera de sus centros de trabajo. EL TRABAJADOR se compromete a desplazarse a cualquier punto de la República del Perú donde su presencia sea necesaria.</p>

<h4>DÉCIMA TERCERA: BUENA FE, EXCLUSIVIDAD Y CONFIDENCIALIDAD</h4>
<p>EL TRABAJADOR se obliga a poner al servicio de EL EMPLEADOR toda su capacidad, diligencia y lealtad. Se compromete a guardar reserva de toda información confidencial de EL EMPLEADOR.</p>

<h4>DÉCIMA CUARTA: PROPIEDAD INTELECTUAL</h4>
<p>Todos los proyectos y productos generados en virtud de la relación laboral serán propiedad de EL EMPLEADOR.</p>

<h4>DÉCIMA QUINTA: ENTREGA DE MATERIALES</h4>
<p>EL TRABAJADOR se obliga a cuidar y mantener en buen estado los bienes, herramientas y equipos de EL EMPLEADOR.</p>

<h4>DÉCIMA SEXTA: EXÁMENES MÉDICOS</h4>
<p>EL TRABAJADOR se someterá a los exámenes médicos programados conforme a la Ley N.&deg; 29783.</p>

<h4>DÉCIMA SÉPTIMA: PROTECCIÓN DE DATOS PERSONALES</h4>
<p>EL TRABAJADOR autoriza el tratamiento de sus datos personales para la ejecución de la relación contractual.</p>

<h4>DÉCIMA OCTAVA: SEGURIDAD Y SALUD EN EL TRABAJO</h4>
<p>Conforme a la Ley N.&deg; 29783, EL EMPLEADOR informa las recomendaciones de SST aplicables al cargo de {{cargo}}.</p>

<h4>DÉCIMA NOVENA: USO DE ALCOHOLÍMETRO</h4>
<p>EL TRABAJADOR acepta ser sometido al uso de alcoholímetro de acuerdo con las políticas de EL EMPLEADOR.</p>

<h4>VIGÉSIMA: COMPETENCIA JURISDICCIONAL</h4>
<p>Las partes se someten a la competencia de los Juzgados Especializados de Trabajo de la Ciudad de Lima, señalando como domicilios los que aparecen en la introducción del presente documento.</p>

<p style="margin-top:25px;">Hecho y firmado en dos (02) ejemplares de un mismo tenor, el día {{fecha_firma}}, en la ciudad de {{ciudad_firma}}, Perú.</p>
"""

# ═══════════════════════════════════════════════════════════════════════════
# PLANTILLA 3: CONTRATO INDEFINIDO
# ═══════════════════════════════════════════════════════════════════════════
CONTRATO_INDEFINIDO = """
<h2 style="text-align:center; color:#0f766e;">CONTRATO DE TRABAJO A PLAZO INDETERMINADO</h2>

<p>Conste por el presente documento, el <strong>CONTRATO DE TRABAJO A PLAZO INDETERMINADO</strong>, que celebran de una parte, <strong>{{empresa}}</strong> con RUC N.&deg; {{ruc_empresa}}, domiciliada en {{direccion_empresa}}, representada por {{representante_legal}}, identificado(a) con {{tipo_doc_representante}} N.&deg; {{nro_doc_representante}}, a quien se denominará <strong>EL EMPLEADOR</strong>, y de la otra parte, <strong>{{nombre_empleado}}</strong>, identificado(a) con {{tipo_doc_trabajador}} N.&deg; {{dni}}, domiciliado en {{domicilio}}, a quien se denominará <strong>EL TRABAJADOR</strong>.</p>

<h4>PRIMERA: OBJETO</h4>
<p>EL EMPLEADOR contrata los servicios de EL TRABAJADOR para que desempeñe el cargo de <strong>{{cargo}}</strong>, debiendo someterse al cumplimiento de las funciones inherentes al puesto y las normas internas de la empresa.</p>

<h4>SEGUNDA: DURACIÓN</h4>
<p>El presente contrato es a <strong>plazo indeterminado</strong>, iniciando el <strong>{{fecha_inicio}}</strong>.</p>

<h4>TERCERA: REMUNERACIÓN</h4>
<p>EL EMPLEADOR abonará una remuneración bruta mensual de <strong>{{remuneracion}}</strong> ({{remuneracion_letras}}), sujeta a las deducciones de ley.</p>

<h4>CUARTA: JORNADA DE TRABAJO</h4>
<p>EL TRABAJADOR cumplirá una jornada de <strong>{{jornada_semanal}} horas semanales</strong>, conforme al D.Leg. N.&deg; 854.</p>

<h4>QUINTA: PERÍODO DE PRUEBA</h4>
<p>EL TRABAJADOR estará sujeto a un período de prueba de <strong>{{periodo_prueba}}</strong>, conforme al artículo 10.&deg; del D.S. N.&deg; 003-97-TR.</p>

<h4>SEXTA: OBLIGACIONES</h4>
<p>EL TRABAJADOR se compromete a cumplir con las funciones del cargo, observar el Reglamento Interno de Trabajo, guardar confidencialidad y cumplir normas de SST.</p>

<h4>SÉPTIMA: CAUSALES DE RESOLUCIÓN</h4>
<p>Son causales de resolución: (a) el mutuo acuerdo; (b) las causas justas de los artículos 23, 24 y 25 del D.S. N.&deg; 003-97-TR; (c) la renuncia con preaviso de 30 días; (d) las demás previstas por ley.</p>

<h4>OCTAVA: DISPOSICIONES FINALES</h4>
<p>Para lo no previsto, se aplica la legislación laboral vigente. Las partes se someten a la jurisdicción de los juzgados del domicilio del empleador.</p>

<p style="margin-top:25px;">Hecho y firmado en dos (02) ejemplares, el día {{fecha_firma}}, en la ciudad de {{ciudad_firma}}, Perú.</p>
"""

# ═══════════════════════════════════════════════════════════════════════════
# PLANTILLA 4: PRÓRROGA DE CONTRATO
# ═══════════════════════════════════════════════════════════════════════════
PRORROGA_CONTRATO = """
<h2 style="text-align:center; color:#0f766e;">PRÓRROGA DEL CONTRATO DE TRABAJO SUJETO A MODALIDAD POR OBRA DETERMINADA</h2>

<p>Conste por el presente documento, que se extiende por duplicado, la <strong>PRÓRROGA DEL CONTRATO DE TRABAJO SUJETO A MODALIDAD POR OBRA DETERMINADA</strong>, que celebran de una parte, <strong>{{empresa}}</strong> con RUC N.&deg; {{ruc_empresa}} y domicilio real en {{direccion_empresa}}, debidamente representada por su apoderado(a) {{representante_legal}}, con {{tipo_doc_representante}} N.&deg; {{nro_doc_representante}}, a quien en adelante se le denominará <strong>EL EMPLEADOR</strong>, y de la otra parte, <strong>{{nombre_empleado}}</strong> con {{tipo_doc_trabajador}} N.&deg; {{dni}}, domiciliado en {{domicilio}}, a quien en adelante se le denominará <strong>EL TRABAJADOR</strong>, en los términos y condiciones siguientes:</p>

<h4>PRIMERA: ANTECEDENTES</h4>
<p>EL EMPLEADOR y EL TRABAJADOR suscribieron un Contrato de Trabajo sujeto a modalidad por Obra determinada — en adelante, EL CONTRATO — para que EL TRABAJADOR ocupe el cargo de <strong>{{cargo}}</strong> desde el {{fecha_inicio_original}} al {{fecha_fin_original}}. Y siendo su última prórroga el {{fecha_fin_anterior}}.</p>
<p>En ese contexto, EL EMPLEADOR necesita seguir contando con la colaboración de una persona capacitada y con experiencia en el campo en el que se especializa EL TRABAJADOR, con la finalidad que siga siendo responsable de ocupar el cargo de <strong>{{cargo}}</strong> en la obra señalada en EL CONTRATO.</p>

<h4>SEGUNDA: OBJETO DE CONTRATACIÓN Y NECESIDAD DE CONTINUAR CON LOS SERVICIOS DE MANERA TEMPORAL</h4>
<p>En el ejercicio ordinario de sus actividades, EL EMPLEADOR ha suscrito un contrato con {{obra_cliente}} para desarrollar la obra denominada «{{obra_nombre}}», en adelante, «LA OBRA».</p>
<p>Con ocasión de la ejecución de estas actividades, y tomando en consideración de que LA OBRA aún continúa desarrollándose, EL EMPLEADOR requiere seguir contando con los servicios de personal debidamente capacitado y especializado para que se dedique al desempeño de determinadas ocupaciones y tareas como se indica en EL CONTRATO.</p>
<p>Por tal motivo la presente prórroga de EL CONTRATO se encuentra sujeta a la modalidad de Obra Determinada, prevista en el artículo 63.&deg; del Texto Único Ordenado del Decreto Legislativo 728, Ley de Productividad y Competitividad Laboral (en adelante LPCL), aprobado por Decreto Supremo No. 003-97-TR.</p>
<p>En consecuencia, las partes acuerdan <strong>Prorrogar EL CONTRATO del {{fecha_inicio}} hasta el {{fecha_fin}}</strong> y concluirá automática e indefectiblemente el día antes señalado sin necesidad de comunicación previa o en la oportunidad que culmine LA OBRA, lo que suceda primero.</p>
<p>La suspensión del contrato de trabajo por alguna de las causas previstas en el artículo 12.&deg; de la LPCL no interrumpirá el plazo de duración del contrato.</p>
<p>Las partes podrán prorrogar o renovar EL CONTRATO las veces necesarias para la conclusión o terminación de la obra o servicio objeto de la contratación, de conformidad con lo señalado en el primer párrafo del artículo 63.&deg; del TUO de la LPCL.</p>

<h4>TERCERA: RATIFICACIÓN Y DECLARACIÓN DE LAS PARTES</h4>
<p>EL TRABAJADOR y EL EMPLEADOR reconocen que las cláusulas descritas anteriormente serán aquellas que regulen, a partir de la suscripción del presente documento, las condiciones laborales entre LAS PARTES en lo que fuera concerniente y haya sido modificado expresamente, dejando establecido que dicha modificación es razonable y que respetan sus derechos, por lo que se suscribe el presente documento de manera libre y voluntaria.</p>
<p>En este sentido, las partes reconocen que la presente prórroga constituye la relación jurídica que mejor se ajusta a sus necesidades y, por eso, ratifican que constituye un acto jurídico válido que no se encuentra afectado por causal de invalidez o ineficacia alguna.</p>
<p>De igual forma, EL TRABAJADOR y EL EMPLEADOR ratifican las condiciones y cláusulas establecidas en EL CONTRATO que no hayan sido modificadas expresamente por el presente documento.</p>

<p style="margin-top:25px;">Hecho y firmado en dos (02) ejemplares de un mismo tenor por EL TRABAJADOR y por EL EMPLEADOR, el día {{fecha_firma}}, en la ciudad de {{ciudad_firma}}, Perú, en señal de entera conformidad y aceptación y para constancia de las partes contratantes.</p>
"""

# ═══════════════════════════════════════════════════════════════════════════
# PLANTILLA 5: ADENDA — AUMENTO SALARIAL
# ═══════════════════════════════════════════════════════════════════════════
ADENDA_AUMENTO_SALARIAL = """
<h2 style="text-align:center; color:#0f766e;">ADENDA AL CONTRATO DE TRABAJO</h2>
<h3 style="text-align:center;">MODIFICACIÓN DE REMUNERACIÓN</h3>

<p>Conste por el presente documento la <strong>ADENDA AL CONTRATO DE TRABAJO</strong> que celebran de una parte, <strong>{{empresa}}</strong> con RUC N.&deg; {{ruc_empresa}}, representada por {{representante_legal}}, a quien se denominará <strong>EL EMPLEADOR</strong>, y de la otra parte, <strong>{{nombre_empleado}}</strong> con {{tipo_doc_trabajador}} N.&deg; {{dni}}, a quien se denominará <strong>EL TRABAJADOR</strong>.</p>

<h4>PRIMERA: ANTECEDENTES</h4>
<p>EL EMPLEADOR y EL TRABAJADOR mantienen una relación laboral vigente, en virtud del contrato de trabajo suscrito el {{fecha_inicio_original}}, donde EL TRABAJADOR desempeña el cargo de <strong>{{cargo}}</strong>.</p>

<h4>SEGUNDA: OBJETO DE LA ADENDA</h4>
<p>Por mutuo acuerdo, las partes convienen en modificar la remuneración mensual de EL TRABAJADOR, de la siguiente manera:</p>
<ul>
<li>Remuneración anterior: <strong>{{sueldo_anterior}}</strong></li>
<li>Nueva remuneración: <strong>{{sueldo_nuevo}}</strong></li>
</ul>
<p>La nueva remuneración será efectiva a partir de {{fecha_adenda}}.</p>

<h4>TERCERA: RATIFICACIÓN</h4>
<p>Las demás cláusulas y condiciones del contrato original que no hayan sido expresamente modificadas por la presente adenda permanecen vigentes y se ratifican en todos sus extremos.</p>

<p style="margin-top:25px;">Firmado en dos (02) ejemplares, el día {{fecha_firma}}, en la ciudad de {{ciudad_firma}}, Perú.</p>
"""

# ═══════════════════════════════════════════════════════════════════════════
# PLANTILLA 6: ADENDA — CAMBIO DE CARGO
# ═══════════════════════════════════════════════════════════════════════════
ADENDA_CAMBIO_CARGO = """
<h2 style="text-align:center; color:#0f766e;">ADENDA AL CONTRATO DE TRABAJO</h2>
<h3 style="text-align:center;">MODIFICACIÓN DE CARGO</h3>

<p>Conste por el presente documento la <strong>ADENDA AL CONTRATO DE TRABAJO</strong> que celebran de una parte, <strong>{{empresa}}</strong> con RUC N.&deg; {{ruc_empresa}}, representada por {{representante_legal}}, a quien se denominará <strong>EL EMPLEADOR</strong>, y de la otra parte, <strong>{{nombre_empleado}}</strong> con {{tipo_doc_trabajador}} N.&deg; {{dni}}, a quien se denominará <strong>EL TRABAJADOR</strong>.</p>

<h4>PRIMERA: ANTECEDENTES</h4>
<p>EL EMPLEADOR y EL TRABAJADOR mantienen una relación laboral vigente, en virtud del contrato de trabajo suscrito el {{fecha_inicio_original}}.</p>

<h4>SEGUNDA: OBJETO DE LA ADENDA</h4>
<p>Por mutuo acuerdo, las partes convienen en modificar el cargo de EL TRABAJADOR, de la siguiente manera:</p>
<ul>
<li>Cargo anterior: <strong>{{cargo_anterior}}</strong></li>
<li>Nuevo cargo: <strong>{{cargo_nuevo}}</strong></li>
</ul>
<p>El cambio será efectivo a partir de {{fecha_adenda}}.</p>

<h4>TERCERA: FUNCIONES DEL NUEVO CARGO</h4>
<p>Las funciones inherentes al nuevo cargo de <strong>{{cargo_nuevo}}</strong> son las siguientes:</p>
{{funciones_cargo}}

<h4>CUARTA: RATIFICACIÓN</h4>
<p>Las demás cláusulas y condiciones del contrato original que no hayan sido expresamente modificadas por la presente adenda permanecen vigentes y se ratifican en todos sus extremos.</p>

<p style="margin-top:25px;">Firmado en dos (02) ejemplares, el día {{fecha_firma}}, en la ciudad de {{ciudad_firma}}, Perú.</p>
"""

# ═══════════════════════════════════════════════════════════════════════════
# PLANTILLA 7: ADENDA — CAMBIO DE CONDICIONES
# ═══════════════════════════════════════════════════════════════════════════
ADENDA_CAMBIO_CONDICIONES = """
<h2 style="text-align:center; color:#0f766e;">ADENDA AL CONTRATO DE TRABAJO</h2>
<h3 style="text-align:center;">MODIFICACIÓN DE CONDICIONES LABORALES</h3>

<p>Conste por el presente documento la <strong>ADENDA AL CONTRATO DE TRABAJO</strong> que celebran de una parte, <strong>{{empresa}}</strong> con RUC N.&deg; {{ruc_empresa}}, representada por {{representante_legal}}, a quien se denominará <strong>EL EMPLEADOR</strong>, y de la otra parte, <strong>{{nombre_empleado}}</strong> con {{tipo_doc_trabajador}} N.&deg; {{dni}}, a quien se denominará <strong>EL TRABAJADOR</strong>.</p>

<h4>PRIMERA: ANTECEDENTES</h4>
<p>EL EMPLEADOR y EL TRABAJADOR mantienen una relación laboral vigente en virtud del contrato suscrito el {{fecha_inicio_original}}, donde EL TRABAJADOR desempeña el cargo de <strong>{{cargo}}</strong>.</p>

<h4>SEGUNDA: OBJETO DE LA ADENDA</h4>
<p>Por mutuo acuerdo, las partes convienen en modificar las condiciones laborales de EL TRABAJADOR:</p>
<p><strong>Tipo de modificación:</strong> {{tipo_modificacion}}</p>
<p><strong>Condición anterior:</strong> {{sueldo_anterior}}</p>
<p><strong>Nueva condición:</strong> {{sueldo_nuevo}}</p>
<p>{{detalle_adenda}}</p>
<p>La modificación será efectiva a partir de {{fecha_adenda}}.</p>

<h4>TERCERA: RATIFICACIÓN</h4>
<p>Las demás cláusulas y condiciones del contrato original permanecen vigentes y se ratifican.</p>

<p style="margin-top:25px;">Firmado en dos (02) ejemplares, el día {{fecha_firma}}, en la ciudad de {{ciudad_firma}}, Perú.</p>
"""

# ═══════════════════════════════════════════════════════════════════════════
# PLANTILLA 8: CONTRATO NECESIDAD DE MERCADO
# ═══════════════════════════════════════════════════════════════════════════
CONTRATO_NECESIDAD_MERCADO = """
<h2 style="text-align:center; color:#0f766e;">CONTRATO DE TRABAJO SUJETO A MODALIDAD POR NECESIDAD DE MERCADO</h2>

<p>Conste por el presente documento, el <strong>CONTRATO DE TRABAJO SUJETO A MODALIDAD POR NECESIDAD DE MERCADO</strong>, que celebran de una parte, <strong>{{empresa}}</strong> con RUC N.&deg; {{ruc_empresa}}, domiciliada en {{direccion_empresa}}, representada por {{representante_legal}}, con {{tipo_doc_representante}} N.&deg; {{nro_doc_representante}}, a quien se denominará <strong>EL EMPLEADOR</strong>, y de la otra parte, <strong>{{nombre_empleado}}</strong> con {{tipo_doc_trabajador}} N.&deg; {{dni}}, domiciliado en {{domicilio}}, a quien se denominará <strong>EL TRABAJADOR</strong>.</p>

<h4>PRIMERA: ANTECEDENTES</h4>
<p>EL EMPLEADOR requiere incrementar su fuerza laboral debido a variaciones sustanciales de la demanda en el mercado, incluso cuando se trate de labores ordinarias que forman parte de la actividad normal de la empresa.</p>

<h4>SEGUNDA: CAUSA OBJETIVA</h4>
<p>El presente contrato se celebra al amparo del artículo 58.&deg; del T.U.O. del D.Leg. N.&deg; 728, aprobado por D.S. N.&deg; 003-97-TR. La causa objetiva que justifica la contratación temporal es el incremento sustancial de la demanda del mercado que requiere contar con personal adicional en el cargo de <strong>{{cargo}}</strong>.</p>

<h4>TERCERA: DURACIÓN</h4>
<p>El contrato rige desde el <strong>{{fecha_inicio}}</strong> hasta el <strong>{{fecha_fin}}</strong>, pudiendo renovarse hasta un máximo de cinco (5) años.</p>

<h4>CUARTA: REMUNERACIÓN</h4>
<p>EL EMPLEADOR abonará una remuneración bruta mensual de <strong>{{remuneracion}}</strong> ({{remuneracion_letras}}), sujeta a deducciones de ley.</p>

<h4>QUINTA: JORNADA</h4>
<p>La jornada será de <strong>{{jornada_semanal}} horas semanales</strong>, conforme al D.Leg. N.&deg; 854.</p>

<h4>SEXTA: PERÍODO DE PRUEBA</h4>
<p>Se pacta un período de prueba de <strong>{{periodo_prueba}}</strong> conforme al art. 10.&deg; del D.S. N.&deg; 003-97-TR.</p>

<h4>SÉPTIMA: OBLIGACIONES</h4>
<p>EL TRABAJADOR se compromete a cumplir las funciones del cargo, observar el RIT, guardar confidencialidad y cumplir normas de SST.</p>

<h4>OCTAVA: DISPOSICIONES FINALES</h4>
<p>Para lo no previsto, rige la legislación laboral vigente. Las partes se someten a los juzgados del domicilio del empleador.</p>

<p style="margin-top:25px;">Firmado en dos (02) ejemplares, el día {{fecha_firma}}, en la ciudad de {{ciudad_firma}}, Perú.</p>
"""

# ═══════════════════════════════════════════════════════════════════════════
# PLANTILLA 9: CONTRATO POR OBRA — GENÉRICO
# ═══════════════════════════════════════════════════════════════════════════
CONTRATO_OBRA_GENERICO = """
<h2 style="text-align:center; color:#0f766e;">CONTRATO DE TRABAJO SUJETO A MODALIDAD POR OBRA DETERMINADA</h2>

<p>Conste por el presente documento, el <strong>CONTRATO DE TRABAJO SUJETO A MODALIDAD POR OBRA DETERMINADA</strong>, que celebran de una parte, <strong>{{empresa}}</strong> con RUC N.&deg; {{ruc_empresa}}, domiciliada en {{direccion_empresa}}, representada por {{representante_legal}}, con {{tipo_doc_representante}} N.&deg; {{nro_doc_representante}}, a quien se denominará <strong>EL EMPLEADOR</strong>, y de la otra parte, <strong>{{nombre_empleado}}</strong> con {{tipo_doc_trabajador}} N.&deg; {{dni}}, domiciliado en {{domicilio}}, a quien se denominará <strong>EL TRABAJADOR</strong>.</p>

<h4>PRIMERA: ANTECEDENTES Y CAUSA OBJETIVA</h4>
<p>EL EMPLEADOR ha suscrito un contrato para la ejecución de la obra denominada «{{obra_nombre}}» con {{obra_cliente}}. Con ocasión de dicha obra, requiere contratar personal para el cargo de <strong>{{cargo}}</strong>.</p>
<p>El contrato se sujeta a la modalidad de Obra Determinada, art. 63.&deg; del D.S. N.&deg; 003-97-TR.</p>

<h4>SEGUNDA: OBJETO</h4>
<p>EL TRABAJADOR prestará servicios en el cargo de <strong>{{cargo}}</strong>, realizando las funciones inherentes al puesto.</p>

<h4>TERCERA: DURACIÓN</h4>
<p>El contrato rige desde el <strong>{{fecha_inicio}}</strong> hasta el <strong>{{fecha_fin}}</strong>, o hasta la conclusión de LA OBRA, lo que suceda primero.</p>

<h4>CUARTA: REMUNERACIÓN</h4>
<p>Remuneración bruta mensual: <strong>{{remuneracion}}</strong> ({{remuneracion_letras}}), sujeta a deducciones de ley.</p>

<h4>QUINTA: JORNADA</h4>
<p>Jornada de <strong>{{jornada_semanal}} horas semanales</strong>, conforme al D.Leg. N.&deg; 854.</p>

<h4>SEXTA: PERÍODO DE PRUEBA</h4>
<p>Período de prueba de <strong>{{periodo_prueba}}</strong> conforme al art. 10.&deg; del D.S. N.&deg; 003-97-TR.</p>

<h4>SÉPTIMA: DISPOSICIONES FINALES</h4>
<p>Para lo no previsto, rige la legislación laboral vigente.</p>

<p style="margin-top:25px;">Firmado en dos (02) ejemplares, el día {{fecha_firma}}, en la ciudad de {{ciudad_firma}}, Perú.</p>
"""


# ═══════════════════════════════════════════════════════════════════════════
# LISTA DE PLANTILLAS
# ═══════════════════════════════════════════════════════════════════════════
PLANTILLAS = [
    {
        'nombre': 'Contrato por Obra — Personal de Confianza',
        'tipo_documento': 'CONTRATO',
        'categoria': 'CONFIANZA',
        'tipo_contrato': 'OBRA_SERVICIO',
        'contenido_html': CONTRATO_CONFIANZA,
    },
    {
        'nombre': 'Contrato por Obra — Personal Fiscalizable',
        'tipo_documento': 'CONTRATO',
        'categoria': 'FISCALIZABLE',
        'tipo_contrato': 'OBRA_SERVICIO',
        'contenido_html': CONTRATO_FISCALIZABLE,
    },
    {
        'nombre': 'Contrato por Obra — Genérico',
        'tipo_documento': 'CONTRATO',
        'categoria': 'OBRA_DETERMINADA',
        'tipo_contrato': 'OBRA_SERVICIO',
        'contenido_html': CONTRATO_OBRA_GENERICO,
    },
    {
        'nombre': 'Contrato Indefinido',
        'tipo_documento': 'CONTRATO',
        'categoria': 'INDEFINIDO',
        'tipo_contrato': 'INDEFINIDO',
        'contenido_html': CONTRATO_INDEFINIDO,
    },
    {
        'nombre': 'Contrato por Necesidad de Mercado',
        'tipo_documento': 'CONTRATO',
        'categoria': 'NECESIDAD_MERCADO',
        'tipo_contrato': 'NECESIDAD_MERCADO',
        'contenido_html': CONTRATO_NECESIDAD_MERCADO,
    },
    {
        'nombre': 'Prórroga de Contrato por Obra',
        'tipo_documento': 'PRORROGA',
        'categoria': '',
        'tipo_contrato': 'OBRA_SERVICIO',
        'contenido_html': PRORROGA_CONTRATO,
    },
    {
        'nombre': 'Adenda — Aumento Salarial',
        'tipo_documento': 'ADENDA',
        'categoria': 'AUMENTO_SALARIAL',
        'tipo_contrato': '',
        'contenido_html': ADENDA_AUMENTO_SALARIAL,
    },
    {
        'nombre': 'Adenda — Cambio de Cargo',
        'tipo_documento': 'ADENDA',
        'categoria': 'CAMBIO_CARGO',
        'tipo_contrato': '',
        'contenido_html': ADENDA_CAMBIO_CARGO,
    },
    {
        'nombre': 'Adenda — Cambio de Condiciones',
        'tipo_documento': 'ADENDA',
        'categoria': 'CAMBIO_CONDICIONES',
        'tipo_contrato': '',
        'contenido_html': ADENDA_CAMBIO_CONDICIONES,
    },
]


class Command(BaseCommand):
    help = 'Crea/actualiza plantillas de contratos laborales basadas en normativa peruana'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Sobrescribir plantillas existentes (por nombre)',
        )

    def handle(self, *args, **options):
        force = options['force']
        created = 0
        updated = 0
        skipped = 0

        for data in PLANTILLAS:
            nombre = data['nombre']
            existing = PlantillaContrato.objects.filter(nombre=nombre).first()

            if existing:
                if force:
                    existing.tipo_documento = data['tipo_documento']
                    existing.categoria = data['categoria']
                    existing.tipo_contrato = data['tipo_contrato']
                    existing.contenido_html = data['contenido_html']
                    existing.activo = True
                    existing.save()
                    updated += 1
                    self.stdout.write(f'  ~ Actualizada: {nombre}')
                else:
                    skipped += 1
                    self.stdout.write(f'  - Omitida (ya existe): {nombre}')
            else:
                PlantillaContrato.objects.create(
                    nombre=nombre,
                    tipo_documento=data['tipo_documento'],
                    categoria=data['categoria'],
                    tipo_contrato=data['tipo_contrato'],
                    contenido_html=data['contenido_html'],
                    activo=True,
                )
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  + Creada: {nombre}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nResultado: {created} creadas, {updated} actualizadas, {skipped} omitidas'
        ))
