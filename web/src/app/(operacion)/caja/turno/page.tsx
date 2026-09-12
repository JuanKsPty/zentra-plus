import { AvisoDeFallo, esFalloDeApi } from '@/components/shared/api-error-notice';
import { ControlDeCaja } from '@/components/caja/shift-control';
import { arqueoDe, turnoActual } from '@/services/cashService.server';

export const metadata = { title: 'Caja · Zentra+' };

export default async function Turno() {
  let datos;
  try {
    const turno = await turnoActual();
    datos = { turno, arqueo: turno ? await arqueoDe(turno.id) : null };
  } catch (error) {
    if (!esFalloDeApi(error)) throw error;
    return <AvisoDeFallo error={error} />;
  }

  return <ControlDeCaja turno={datos.turno} arqueo={datos.arqueo} />;
}
