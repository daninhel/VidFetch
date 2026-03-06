
export function sanitizeFilename(name: string): string {
    const cleaned = name.replace(/[^\w\s-]/g, '');
    return cleaned.substring(0, 200) || 'video';
}

export function validateYoutubeUrl(url: string | undefined): { isValid: boolean; error?: string } {
    if (!url || url.trim() === '') {
        return { isValid: false, error: 'A URL do vídeo é obrigatória (ex: ?url=https://youtube.com/...)' };
    }

    try {
        const parsedUrl = new URL(url);

        if (parsedUrl.protocol !== 'https:' && parsedUrl.protocol !== 'http:') {
            return { isValid: false, error: 'Protocolo de URL não suportado. Use http ou https.' };
        }

        const host = parsedUrl.hostname.replace(/^www\./, '').toLowerCase();

        if (host !== 'youtube.com' && host !== 'youtu.be') {
            return { isValid: false, error: 'Domínio não autorizado. Use apenas links do YouTube.' };
        }

        if (host === 'youtube.com' && !parsedUrl.searchParams.has('v') && !parsedUrl.pathname.startsWith('/shorts/')) {
            return { isValid: false, error: 'URL do YouTube não possui ID de vídeo.' };
        }
    } catch (err: any) {
        return { isValid: false, error: 'Formato de URL inválido.' };
    }

    return { isValid: true };
}

export function handleYoutubeError(error: any): { status: number; message: string; suggestion?: string; isAuthError: boolean } {
    const errMessage = (error.message || '').toLowerCase();
    const statusCode = error.statusCode || 500;

    const isAuthError = statusCode === 403 ||
        errMessage.includes('sign-in required') ||
        errMessage.includes('sign in to confirm your age') ||
        errMessage.includes('bot');

    if (isAuthError) {
        return {
            status: 403,
            message: 'Acesso restrito: O YouTube bloqueou a requisição ou exigiu login (403 Forbidden).',
            suggestion: 'Atualize os cookies exportando um formato JSON recente para a variável YOUTUBE_COOKIES na Vercel.',
            isAuthError: true
        };
    }

    if (errMessage.includes('video unavailable') || statusCode === 404) {
        return {
            status: 404,
            message: 'Vídeo indisponível, privado ou removido.',
            isAuthError: false
        };
    }

    return {
        status: 500,
        message: 'Falha interna ao se comunicar com o YouTube.',
        isAuthError: false
    };
}
